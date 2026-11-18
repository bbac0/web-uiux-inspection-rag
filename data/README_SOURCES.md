# RAG 근거 문서

이 저장소에는 PDF 원본을 포함하지 않으며, 아래 출처 사이트에서 받아 `data/` 아래에 두고 색인 스크립트를 실행하면 된다.
받은 파일이 실험에 쓴 파일과 같은지는 아래 SHA-256 으로 확인할 수 있다.

| 파일명 | SHA-256 | 쪽수 | 크기 (바이트) | 청크 수 | 출처 |
|---|---|---|---|---|---|
| `gov_guide.pdf` | `a3edec995dac140d066469a5e072652c9b20c0ef0a3d77bf9277998b0dee8f30` | 1,181 | 40,362,236 | 732 | 아래 1절 |
| `gov_check.pdf` | `af6cc8a981d0b9590dcc16e5a4a4f009c3dba7effd7de402eb4c9822cf61ba6e` | 273 | 7,727,018 | 288 | 아래 1절 |

- 쪽수: PyPDF2 `PdfReader(...).pages` 로 셈.
- 청크 수: 실험에 쓴 ChromaDB(`services/chroma_db`)의 청크 1,020개를 문서별로 나눈 값
  (`results/revision/fixed_query_embedding/ranking.csv` 의 source 열; 분석 계획 `results/revision/analysis_plan.md` 의 1,020청크와 같다).

## 1. 출처

- 두 문서의 출처: 행정안전부, KRDS(범정부 UI/UX 디자인시스템) https://www.krds.go.kr/html/site/outline/outline_05.html
- `gov_guide.pdf`: 「디지털 정부서비스 UI/UX 가이드라인」 2025년 8월 판
  (참고: 행정안전부 공공서비스혁신과 수정본('25.8.) 배포 안내, 2025.09.01,
  https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000045&nttId=120220)
- `gov_check.pdf`: 「디지털 정부 서비스 UI/UX 가이드라인 자체 검증 체크리스트」 표지 날짜 2024.11., KRDS 게시 등록일 2024.12.16

## 2. 이용 조건

- 공공누리 제1유형(출처표시, 상업적 이용·변경 허용). 출처 표시 문구는 저장소 루트의 `NOTICE` 를 보라.
- 이 저장소에는 PDF 원본을 포함하지 않는다. 위 사이트에서 받아 `data/` 아래에 두고 색인 스크립트(아래)를 실행하면 된다.

## 인덱스를 다시 만드는 명령

```bash
# 1) 위 두 PDF 를 data/ 에 둔다.
# 2) 임베딩 API 키를 환경변수 GEMINI_API_KEY 로 설정한다(.env 또는 셸).
python services/indexer.py
```

- `services/indexer.py`: PyPDFLoader 로 읽고 `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)` 로 나눈 뒤
  `models/gemini-embedding-001` 임베딩으로 `./chroma_db` 에 10개씩 넣는다.
- 실험 코드는 `services/chroma_db` 를 쓴다(`experiments/revision/run_experiment.py --chroma-path services/chroma_db`).
  새로 만든 `./chroma_db` 를 쓰려면 그 경로를 지정하거나 `services/chroma_db` 로 옮긴다.
- 임베딩은 API 호출로 다시 계산되므로, 다시 만든 인덱스가 원래 인덱스와 같은 벡터·검색 순위를 낸다는 보장은 없다.
  원래 인덱스의 고정 질의 검색 순위는 `results/revision/fixed_query_embedding/ranking.csv` 에 있다.
