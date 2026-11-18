# 분석 계획 부록: R-full (전체 색인으로 주 조건 R 1회 재실행)

작성 2026-11-19. **실행 전에 커밋한다.** 결과를 보기 전에 정의·비교·지표를 고정하며, 기존 분석 계획과 부록은 고치지 않는다.
연구자 지시(2026-11-19)에 따른 추가 실행이다.

## 1. 목적

주 비교(R 대 A1)에서 RAG 효과가 거의 없었던 결과가 실험 인덱스의 부분 색인(gov_guide 1,181쪽 중 1~736쪽 범위의 721쪽,
1,020청크)에서 비롯된 것인지 확인한다.

## 2. 조건 정의 (R-full)

- 실행 이름 `E1-Rfull-r1`, 조건 이름 `R-full`. 1회 실행.
- E1-R1 과 같은 설정: `experiments/revision/run_experiment.py --pages all --max-pages 1 --prompt-date 2026-11-11
  --concurrency 1`, 고정 질의 "웹 UI/UX 표준 가이드라인 공통 규정", K=4, 스크린샷 + HTML, `models/gemini-2.5-flash`,
  temperature 0, 같은 프롬프트, testbed_200 200페이지. 점수 게이트(cli.py 의 임계값)는 실험 러너에서 쓰지 않는다(E1-R1 과 같음).
- 다른 점: `--chroma-path results/revision/full_index/chroma_db` (1,485청크: gov_check 288 + gov_guide 1,197).
  러너는 이 DB 를 임시 폴더로 복사해서 쓰므로 원본 DB 는 바뀌지 않는다. 실험 DB(`services/chroma_db`)는 쓰지 않는다.
- 전체 색인은 이 컴퓨터의 pypdf 6.16.2 로 추출해 임베딩을 다시 계산한 것이다(`reports/q9_full_index_compare.md`).
  따라서 색인 범위 외에 일부 청크 본문(실험 DB 1,020개 중 19개, 주로 목차)과 임베딩 값도 실험 DB 와 다를 수 있다.
- 전체 색인 사용 확인: 호출 기록 `calls.jsonl` 의 `rag.chunks` 에 기록된 문서·쪽 번호와 `rag.chroma_path` 출처.
- 출력: `results/revision/runs/E1-Rfull-r1/` (추가 전용, 러너가 잠글 때 SHA256SUMS 생성). 기존 run 은 고치지 않는다.

## 3. 채점

- 주 채점기: 의미 채점 pass1(`scoring/semantic_grader_anthropic.py`, 기존과 같은 설정·프롬프트), 잘린 응답은 기존 재채점
  규칙(retry800)으로 다시 채점한 뒤 병합(`semantic_pass1_merged`). Anthropic 배치 제출은 연구자가 한다.
- 보조: 키워드 채점, string_match(용어 유형만). 모두 기존 코드 그대로.

## 4. 비교와 지표

- 비교 대상: E1-R1(같은 설정, 실험 인덱스), E2-A1-1(RAG 끔).
- 지표: 셀(페이지 × 5유형) 단위 마이크로 평균 MCC, 정밀도, 재현율, 유형별 TP/FP/FN/TN. 라벨 nominal 과 effective.
- 구간: 짝 템플릿 군집 부트스트랩(템플릿 10개, B=10,000, numpy default_rng 시드 20261111, 백분위 95%),
  R-full − R1, R-full − A1-1 의 MCC 차이(마이크로와 유형별). 기존 E7 최종과 같은 함수.
- 그 밖에 보고: 고정 질의로 검색된 4청크의 문서·쪽(페이지 간 동일 여부), 표준 용어 유형의 탐지 페이지·TP/FP,
  출처 인용 점검(제공 청크 일치 비율, 코퍼스 밖 인용, 쪽 [12] 인용; paper_numbers 10절과 같은 정의),
  키워드·string_match 결과.
- 이 실행은 1회다. 반복·추가 분석을 하면 보고서에 사후 분석으로 따로 표시한다. 결과 해석은 보고서에 쓰지 않는다.

## 5. 비용 상한

- 생성 + 의미 채점 합계 $3.5. E1-R1 실측으로 추정: 생성 $2.014(200호출) + 의미 채점 pass1 배치 $0.642 + 재채점 $0.021
  = 약 $2.68.
- 실행 중 누적이 $3.15(90%)를 넘으면 중단한다. 생성 단계에서는 채점 추정치($0.66)를 남겨 두기 위해 생성 누적이
  $2.49 를 넘으면 생성을 멈춘다(누적 감시는 calls.jsonl 의 호출별 cost_usd 합계).
