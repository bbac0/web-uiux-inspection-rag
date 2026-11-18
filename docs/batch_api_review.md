# 의미 채점기에 Message Batches 경로(--batch)를 추가하는 방안 검토 (구현 안 함)

작성 2026-11-12. 대상: `scoring/semantic_grader_anthropic.py`. 근거: Anthropic SDK 문서(Python Message Batches).

## 1. 가능 여부

가능하다. Message Batches 는 Messages API 요청을 비동기로 처리하며, 같은 `params`(model, max_tokens, messages, thinking, output_config 등)를 받는다.

- 배치당 최대 100,000 요청 또는 256 MB. 대부분 1시간 안에 끝나고 최대 24시간. 결과는 생성 후 29일 동안 받을 수 있다.
- 모든 토큰 비용이 표준 가격의 50%.
- 흐름: `client.messages.batches.create(requests=[{custom_id, params}, ...])` → `client.messages.batches.retrieve(id)` 로 `processing_status == "ended"` 까지 대기 →
  `client.messages.batches.results(id)` 로 결과 스트림을 받아 `custom_id` 로 대응(결과 순서는 보장되지 않음).
- 결과 유형: `succeeded`(메시지 포함), `errored`(invalid_request 는 요청 수정 필요, 그 밖은 재시도 가능), `canceled`, `expired`(재제출).

## 2. 필요한 변경

| 영역 | 변경 |
|---|---|
| 요청 생성 | 이슈마다 지금과 같은 `build_input` → `build_request` 로 params 를 만든다(같은 프롬프트, 같은 설정, 같은 누출 검사). |
| custom_id | 현재 issue_id(`E1-R1:page_001:00`)에는 `:` 가 있어 custom_id 형식(영문·숫자·`_`·`-`, 64자 이하)에 맞지 않는다. `{run}__{page}__{idx}__p{pass}` 같은 대체 문자열이나 issue_id 의 짧은 해시로 바꾸고, 대응표를 폴더에 저장한다. |
| 제출 기록 | `batches.jsonl` 에 batch_id, 제출 시각(UTC), 요청 수, custom_id 목록 SHA-256, 설정 SHA-256 을 남긴다(append 전용). 제출 직후 기록해 프로세스가 죽어도 결과를 회수할 수 있게 한다. |
| 결과 회수 | `--batch-collect <batch_id>` 처럼 제출과 회수를 분리한다. 회수 시 결과를 custom_id 로 이슈에 붙여 기존과 같은 `grades.jsonl` 레코드 형식으로 쓴다. |
| 재개(--resume) | 기존 규칙과 같다. (issue_id, pass) 가 최종 상태인 이슈는 다시 제출하지 않는다. 제출됐지만 아직 회수하지 않은 batch_id 가 있으면 새 제출 전에 먼저 회수한다(중복 채점 방지). |
| 오류 처리 | `errored`/`expired` 는 레코드에 result_type 과 오류 유형을 남기고 상태를 api_error 로 둔다. 재제출은 새 배치로 하고 원래 batch_id 와 연결해 기록한다. 배치 생성 자체가 크레딧 부족(400/402)으로 실패하면 즉시 멈춘다. |
| SDK 인자 | thinking·output_config 를 SDK 타입이 모르면, 배치 params 는 JSON 으로 보내지므로 dict 로 그대로 넣으면 된다(동기 경로의 extra_body 전환이 필요 없을 수 있음). 설치되는 SDK 버전에서 확인해야 한다. |

## 3. 위험과 대응

| 위험 | 내용 | 대응 |
|---|---|---|
| 비동기 결과 수집 | 결과가 최대 24시간 뒤에 오고 순서가 없다. 프로세스가 중간에 죽으면 제출한 배치를 잃을 수 있다. | 제출 즉시 batch_id 를 디스크에 기록, 회수 단계를 분리, custom_id 로만 대응. 29일 안에 회수. |
| 로그 형식 | 동기 경로의 `ts_start_utc`/`ts_end_utc`/`latency_sec`/`attempts` 는 요청 단위로 존재하지 않는다. | 레코드에 `mode: "batch"`, `batch_id`, `custom_id`, `result_type`, 배치 제출·종료 시각을 넣고 요청 단위 지연시간은 null 로 둔다. 동기 레코드와 같은 키를 유지하고, 분석 스크립트는 `mode` 로 구분한다. |
| 모델 버전 기록 | 동기 경로와 마찬가지로 결과 메시지의 `model` 문자열을 레코드에 남긴다. 한 배치 안에서도 요청마다 기록한다. | 결과 회수 시 `result.message.model` 과 `usage`(input/output 토큰)를 그대로 저장. 배치 안 모델 버전 종류 수를 요약에 집계. |
| 결과 동등성 | 배치와 동기 호출은 같은 모델·설정이지만 샘플링이 결정적이지 않아(temperature 미지정) 라벨이 다를 수 있다. 실행 경로가 바뀌면 pass1 결과의 성격이 달라진다. | 한 run 의 pass1 은 한 경로(동기 또는 배치)로만 채점한다. 경로를 사전 지정에 적는다. 섞어야 하면 경로를 레코드에 남기고 경로별 일치도를 보고한다. |
| 크레딧·한도 | 배치 생성 시 크레딧 부족이면 거부된다. 처리 중 한도에 걸리면 일부가 errored 로 끝날 수 있다. | 생성 실패는 즉시 중단. errored 비율을 요약에 집계하고, 20% 를 넘으면 재제출 전에 보고. |
| 비용 계산 | 단가가 50% 이므로 비용 기록 방식이 다르다. | 레코드에 `pricing: "batch"` 를 남기고 요약에서 동기·배치 비용을 따로 계산. |

## 4. 판단

- 채점 호출 수(본 실험 pass1 + R1 pass2 + 민감도 채점, 그리고 E9)를 생각하면 50% 절감은 의미가 있다.
- 다만 위의 '결과 동등성' 문제 때문에 **pass1 을 시작하기 전에 경로를 정해야 한다.** 동기 경로로 시작한 run 을 배치로 잇는 것은 권하지 않는다.
- 구현은 승인 후 새 파일(`scoring/semantic_grader_batch.py`)로 하고, 기존 동기 채점기의 프롬프트·설정·누출 검사·파싱 함수를 그대로 import 해 쓴다. 가짜 배치 클라이언트로 단위 테스트한 뒤 실제 사용한다.

## 5. 배치 요청에서 thinking between_tools 와 output_config effort 지원 여부 (2026-11-12 확인)

결론: **문서상 지원된다.** 근거(Anthropic SDK 문서, Claude API 스킬에 포함된 최신 문서 기준):

| 확인 항목 | 문서 근거 |
|---|---|
| 배치가 Messages API 기능을 그대로 받는가 | Batch 문서: "All Messages API features supported". 배치 `params` 는 `messages.create` 와 같은 요청 본문이다. |
| `output_config: {"effort": ...}` | Python 배치 공식 예제(end-to-end)가 배치 params 안에 `output_config={"effort": "low"}` 를 넣는다. |
| `thinking: {"type": "between_tools"}` | Claude Sonnet 5.5 마이그레이션 문서: "needs no beta header and works on every platform that offers the model". 같은 문서의 "Carries over" 목록에 batch processing 이 있다. 제한: Claude Sonnet 5.5 전용, `thinking` 안에 다른 필드 금지, **effort `high` 이하에서만**(우리 설정 `high` 는 허용), 메시지별 effort 변경 불가(우리는 쓰지 않음). |
| Python SDK 에서 넘기는 방법 | 문서: Python 에서는 `between_tools` 를 `thinking` 객체의 일반 값으로 쓴다. 배치 params 는 JSON 으로 전송되므로 타입 문제는 없다. |

한계: 배치 문서 예제에 `between_tools` 자체가 나오지는 않는다(문서 간 조합으로 확인). 배치 경로가 선택되면 본 채점 전에 **1건짜리 확인 배치**
(같은 설정, 이슈 1건, 결과 미사용)를 보내 수락 여부와 응답 형태(text 블록, stop_reason, model)를 확인한다. 거부되면 사전 규칙에 따라 표준 경로로 확정한다.

