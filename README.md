# LinkUp: LLM 기반 웹 UI/UX 가이드라인 자동 검수 시스템

정부 UI/UX 가이드라인(PDF)을 근거 문서로 삼아, 웹페이지의 스크린샷과 HTML을 멀티모달 LLM(Gemini 2.5 Flash)으로 분석하고 디자인·운영·기술 영역의 결함을 보고하는 시스템입니다. 가이드라인은 ChromaDB 벡터 저장소에 색인되어 검색 증강(RAG) 컨텍스트로 프롬프트에 포함됩니다.

이 저장소는 (1) 웹 서비스 코드와 (2) 논문의 Results 절에 보고한 실험의 스크립트·데이터·결과를 함께 담고 있습니다.

## 저장소 구성

```
main.py, run.py            FastAPI 백엔드 (분석 API, SSE 진행률 스트리밍)
cli.py                     CI/CD용 명령줄 검수 도구 (실험 실행에도 사용)
services/
  analyzer.py              크롤링 → 스크린샷/HTML 수집 → RAG 검색 → Gemini 분석 → 리포트 병합
  indexer.py               가이드라인 PDF를 청크로 나눠 ./chroma_db 에 색인
  scraper.py               Playwright 수집 유틸리티
frontend/                  Streamlit 웹 UI
data/                      가이드라인 PDF (gov_guide.pdf, gov_check.pdf)

testbed_200/               평가용 테스트베드 200페이지 + 정답 메타데이터(dataset_metadata.json)
testbed/                   구간별 지연시간 측정용 50페이지
experiments/               논문 실험 스크립트
paper_results/             논문 수치의 근거가 되는 실행 결과
```

## 설치

Python 3.10 이상에서 동작을 확인했습니다.

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

프로젝트 루트에 `.env` 파일을 만들고 Gemini API 키를 넣습니다.

```
GEMINI_API_KEY=your_key_here
```

가이드라인 벡터 DB를 생성합니다(최초 1회, `./chroma_db` 생성).

```bash
python services/indexer.py
```

## 웹 서비스 실행

```bash
python run.py                       # 백엔드: http://127.0.0.1:8000
streamlit run frontend/app.py       # 프론트엔드 (별도 터미널)
```

명령줄에서 단일 사이트를 검수하려면 다음을 실행합니다.

```bash
python cli.py --url https://example.com --threshold 70 --output audit_report.json
```

## 논문 실험 재현

모든 스크립트는 **저장소 루트에서** `python experiments/<script>.py` 형태로 실행합니다. 스크립트는 기본적으로 `./results/` 에 결과를 씁니다(`.gitignore` 대상). `RESULTS_DIR` 환경변수를 지원하는 스크립트는 이를 `paper_results/run2` 로 지정해 보관된 리포트를 다시 채점할 수 있습니다.

```bash
pip install -r experiments/requirements.txt
```

### 실험과 파일 대응

| 논문 절 | 내용 | 스크립트 | 보관 결과 |
|---|---|---|---|
| 실험 설정 | 200페이지 테스트베드 생성 (10개 템플릿 × 5개 결함 유형, 대조군 39개) | `generate_200_testbed.py` | `testbed_200/` |
| 실험 설정 | CLI로 200페이지 순차 분석 (임계값 0) | `run_batch_v2.py` | `paper_results/run2/` (리포트 200개 + `run_manifest.json`) |
| 정량적 탐지 성능 (Table: performance, category) | 키워드 채점 | `evaluate_performance_v5.py` | 표준 출력 |
| 〃 | 의미 기반 채점 (LLM 분류) | `semantic_issue_classifier.py` | `paper_results/run1/semantic_scoring_run1.json` |
| 반복 실행 (Table: repeat run) | 두 번째 실행의 키워드 채점 | `evaluate_performance_v5.py` | `paper_results/run2/` |
| axe-core 비교 | axe-core v4.14.0 기본 구성 스캔 | `run_axe_core_scan.py` | `paper_results/axe_core/axe_core_scan.json` |
| 〃 | id 중복 룰 비활성화 원인 진단 (`page_065`) | `diagnose_axe_duplicate_id.py` | 표준 출력 |
| 입력 모달리티 Ablation | 스크린샷+HTML / 스크린샷만 / HTML만 (57페이지) | `modality_ablation.py` | `paper_results/modality_ablation/` |
| 처리 속도 (종단) | CLI 1회 실행 시간 | `run_batch_v2.py` | `paper_results/run2/run_manifest.json` (`elapsed_sec`) |
| 처리 속도 (구간별) | 50페이지 × 3회, `file://` 로컬 환경 | `measure_latency.py` | `paper_results/latency/` |
| Discussion: 점수·근거 필드 | 점검 항목 수, 점수 분포, 근거 파일명 점검 | `audit_pipeline_artifacts.py` | 표준 출력 |
| Discussion: 명도 대비 수치 | 보고된 대비비와 WCAG 공식값 비교 | `audit_contrast_ratios.py` | `paper_results/run1/contrast_audit_run1.csv` |
| Discussion: RAG | 고정 검색 질의가 가져오는 청크 확인 | `show_fixed_retrieval.py` | 표준 출력 |
| Discussion: RAG (예비) | 표준 용어 위반 45페이지, RAG 포함/제외 비교 | `rag_ablation.py` | `paper_results/rag_ablation/` |

### 실행 예시

**1. 테스트베드 분석 (탐지 성능, 종단 지연시간)**

```bash
python -m http.server 8080                  # 터미널 1: 루트에서 테스트베드 제공
python experiments/run_batch_v2.py          # 터미널 2: results/report_page_XXX.json 생성
python experiments/evaluate_performance_v5.py
python experiments/semantic_issue_classifier.py
```

보관된 두 번째 실행 결과를 다시 채점하려면:

```bash
RESULTS_DIR=paper_results/run2 python experiments/evaluate_performance_v5.py
# Windows PowerShell: $env:RESULTS_DIR="paper_results/run2"; python experiments/evaluate_performance_v5.py
```

**2. axe-core 비교**

[axe-core v4.14.0](https://github.com/dequelabs/axe-core/releases/tag/v4.14.0)의 `axe.min.js` 를 저장소 루트에 내려받은 뒤 실행합니다(`npm pack axe-core@4.14.0` 으로도 받을 수 있습니다).

```bash
python experiments/run_axe_core_scan.py
python experiments/diagnose_axe_duplicate_id.py
```

**3. 입력 모달리티 Ablation**

논문과 같은 표본을 쓰려면 보관된 `sample.json` 을 먼저 복사합니다. 이 파일이 있으면 스크립트가 새로 추출하지 않고 이 표본을 사용합니다.

```bash
mkdir -p results/modality_ablation
cp paper_results/modality_ablation/sample.json results/modality_ablation/
python experiments/modality_ablation.py run
python experiments/modality_ablation.py score
```

**4. 구간별 지연시간 / RAG 예비 실험**

이 두 스크립트는 벡터 DB 경로 기본값이 `./services/chroma_db` 입니다. `indexer.py` 로 만든 DB를 쓰려면 경로를 지정합니다.

```bash
CHROMA_DB_PATH=./chroma_db python experiments/measure_latency.py
CHROMA_DB_PATH=./chroma_db python experiments/rag_ablation.py
```

## 결과 데이터에 대한 참고

- **첫 번째 실행**의 원본 리포트는 두 번째 실행에 덮어써져 보존되지 않았습니다. `paper_results/run1/` 에는 첫 번째 실행 직후 생성한 의미 기반 채점 결과와 명도 대비 감사 결과만 있습니다. 첫 번째 실행의 키워드 채점 수치는 실행 직후 출력된 값입니다.
- `paper_results/run2/` 는 같은 설정으로 다시 실행한 두 번째 실행의 원본 리포트 200개와 실행 기록입니다.
- `paper_results/rag_ablation/human_review_graded_by_claude.csv` 의 탐지 판정은 사람이 아니라 Claude가 응답을 읽고 한 번 판정한 결과입니다. 판정 기록은 `rag_ablation_graded_by_claude.py` 에 있습니다.
- `paper_results/latency/` 의 로컬 파일 경로는 `file:///<repo>/` 로 익명화했습니다.
- LLM 출력은 생성 온도 0에서도 실행마다 달라질 수 있어, 다시 실행하면 수치가 논문과 정확히 일치하지 않을 수 있습니다(논문의 반복 실행 결과 참고).

## 공개본의 경로 치환과 해시

동결 매니페스트와 SHA256SUMS의 해시는 원본(경로 치환 전) 기준이며, 치환은 scripts/redact_home_paths.py로 재현된다.

- 공개본에서는 Windows 사용자 홈 경로(드라이브:\Users\<이름> 와 슬래시 표기)를 `<HOME>` 으로 바꾸었다.
- 바뀐 파일의 치환 전 해시는 `SHA256SUMS.original`, 치환 후 해시는 `SHA256SUMS.public` 에 있다(형식 `<해시>  <경로>`).
- 원본 저장소 내용에 `python scripts/redact_home_paths.py --root <폴더>` 를 실행하면 같은 공개본이 나온다.
- RAG 근거 PDF 두 개는 공개본에 넣지 않았다. 해시와 인덱스 재생성 방법은 `data/README_SOURCES.md` 에 있다.
- 평가자 CSV 공개용 복사본과 원본 해시는 `PUBLIC_RATER_DATA.md` 에 있다.

## 공개본 안내

- 이 저장소의 테스트 페이지(`testbed_200/`, `testbed_e9/`)는 실험을 위해 만든 **합성 테스트 페이지이며 정부24 등 실제 기관과 무관하다.**
  페이지 제목·문구에 쓰인 서비스 이름과 저작권 표기는 실제 서비스를 흉내 낸 예시일 뿐이다.
- **정부 가이드라인 PDF(`gov_guide.pdf`, `gov_check.pdf`)는 포함하지 않으며 행정안전부 KRDS(https://www.krds.go.kr/html/site/outline/outline_05.html)에서 받아야 한다.**
  파일 이름, SHA-256, 출처는 `data/README_SOURCES.md` 에 있다.
- 출처 표시: 저장소에 인용된 정부 가이드라인 단락의 출처와 이용 조건(공공누리 제1유형)은 [`NOTICE`](NOTICE) 를 보라.
- 라이선스: 코드는 `LICENSE`(MIT), 데이터는 `LICENSE-DATA.md`(CC BY 4.0, 적용 제외 항목 포함)를 따른다.
- 해시 검증: 홈 경로를 `<HOME>` 으로 바꾼 파일(86개, 주로 run 폴더의 `calls.jsonl`, `run_meta.json`, `summary.json`)은
  run 폴더의 `SHA256SUMS`(원본 기준)와 맞지 않는다. 이 파일들은 루트의 `sha256sum -c SHA256SUMS.public` 으로 검증하고,
  원래 해시는 `SHA256SUMS.original` 에 있다(run 폴더 `SHA256SUMS` 의 값과 같다).
- E1~E4 run(파일럿 포함)과 R-full 의 스크린샷(`shots/`)과 프롬프트 원문(`prompts/`)은 원래 버전 관리 대상이 아니었으나,
  이 공개본에는 실행 당시 원본 파일 그대로 넣었다(v4.2). 각 run 폴더의 SHA256SUMS 값과 일치한다.
- pilot-01 의 `calls.jsonl`, `reports.jsonl`, `summary.md` 3개 파일은 그 폴더의 SHA256SUMS 와 맞지 않는다. 이 run 은
  줄바꿈 변환을 막는 설정(`.gitattributes`)이 생기기 전에 커밋되어, 저장소에 넣을 때 줄바꿈이 CRLF → LF 로 바뀌었다.
  SHA256SUMS 는 실행 직후의 원본(CRLF) 파일로 계산한 값이며, 원본 작업 폴더의 파일은 SHA256SUMS 와 일치한다.
  파일 내용(줄바꿈 외)은 같다. pilot-01 은 논문 결과에 쓰지 않은 파일럿 실행이다(크레딧 소진으로 중단).

## R-full: 전체 색인으로 주 조건 R 1회 재실행

- 조건: 주 조건 R(E1-R1)과 같은 설정(고정 질의 "웹 UI/UX 표준 가이드라인 공통 규정", K=4, 스크린샷 + HTML, `gemini-2.5-flash`,
  temperature 0, 같은 프롬프트, testbed_200 200페이지)에서 **검색 인덱스만** 전체 색인으로 바꾼 1회 실행이다.
  실험 인덱스는 gov_guide 1~736쪽 범위의 721쪽(1,020청크)만 담고 있었고, 전체 색인은 1,485청크(가이드라인 1,197 + 체크리스트 288)다.
- 사전 지정: `results/revision/analysis_plan_addendum_rfull.md`. 보고서: `results/revision/reports/rfull_report.md`
  (지표 CSV: `results/revision/rfull/`).
- 실행 폴더: `results/revision/runs/E1-Rfull-r1/` (calls.jsonl, reports.jsonl, summary.json, run_meta.json, SHA256SUMS).
  스크린샷(`shots/`)과 프롬프트 원문(`prompts/`)도 들어 있다(원본 파일 그대로, SHA256SUMS 와 일치).
- 채점 폴더: `results/revision/semantic_scores/E1-Rfull-r1-sem-p1/`(1차), `E1-Rfull-r1-sem-p1-retry/`(잘림 16건 재채점),
  병합 이슈표 `results/revision/issue_tables_merged/E1-Rfull-r1.csv`, 재채점 대상 `results/revision/semantic_truncation_targets_rfull.csv`.
- 전체 색인: `results/revision/full_index/chroma_db/` (약 33 MiB). 만든 방법과 실험 인덱스와의 비교는
  `experiments/revision/full_index_compare.py`, `results/revision/reports/q9_full_index_compare.md`.
- 재현 명령 (API 키는 환경변수로만):

```bash
python -m http.server 8080 --bind 127.0.0.1      # 저장소 루트, 별도 터미널
python experiments/revision/run_experiment.py --run-id E1-Rfull-r1 --condition R-full --pages all --max-pages 1 \
    --chroma-path results/revision/full_index/chroma_db --prompt-date 2026-11-11 --concurrency 1
python scoring/semantic_grader_batch.py submit --run-id E1-Rfull-r1 --out-id E1-Rfull-r1-sem-p1 --pass 1
python scoring/semantic_grader_batch.py collect --out-id E1-Rfull-r1-sem-p1
python experiments/revision/rfull_retry_targets.py
python scoring/semantic_grader_retry.py submit --orig-out-id E1-Rfull-r1-sem-p1 \
    --targets results/revision/semantic_truncation_targets_rfull.csv --config scoring/grader_config_retry800.json
python scoring/semantic_grader_retry.py collect --out-id E1-Rfull-r1-sem-p1-retry
python scoring/issue_table_merged.py --run-id E1-Rfull-r1 --out results/revision/issue_tables_merged/E1-Rfull-r1.csv
python experiments/revision/rfull_report.py
```

## 변경 기록

- v4.2: R-full 산출물 추가; E1~E4·파일럿·R-full 실행의 스크린샷과 프롬프트 원문 추가; `.github/workflows/` 삭제;
  pilot-01 해시 불일치 사유 기록
