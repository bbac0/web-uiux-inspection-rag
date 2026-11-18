# 확정: 짝 템플릿 군집 부트스트랩 (2026-11-13)

- 연구자 지시로 확정 보관한다. 이후 다시 계산하지 않으며, 아래 해시의 파일이 기준이다.
- 분석 상태: **added after seeing replicate results, before semantic scoring** (사전 지정 5절에 덧붙인 강건성 분석).
- 주 비교: **E1-R1 − E2-A1-1 (사전 지정)**. E1-R2 − E2-A1-2, E1-R3b − E2-A1-3 은 **반복 재현(replication)**.
- 방법: 같은 재표집 템플릿을 두 조건에 함께 적용, B = 10,000, numpy default_rng 시드 20261111, 백분위수 95% 구간. LOTO 차이(10개 값 범위, jackknife SE) 같은 표.
- 지표: MCC, 정밀도, 특이도, 재현율의 차이와 구간(csv 는 유형별 전체, tex 는 5유형 합산과 용어 유형). 기존 exact McNemar 는 보조로 같은 행에 있고 군집을 고려하지 않는다는 주석이 있다.
- 생성 커밋: `db8fe98d18bf34f5547bd8ccea91360f99b0ccff` (스크립트 `experiments/revision/e7_paired_cluster.py`)

| 파일 | SHA-256 |
|---|---|
| `results/revision/e7/paired_cluster_bootstrap.csv` | `eb7936a17bf8b4dd23a7271e35456c4ae0d9ad020ea8e318bb6d62fe6d7e663b` |
| `results/revision/e7/paired_cluster_bootstrap.tex` | `951f638b61d431241f8a84274a5dc0f6adfbd535377528323cc283ec61ebf2be` |
| `experiments/revision/e7_paired_cluster.py` | `78df258f36032ed95660a17abf5598855bb0cd262bb6e3e0b73d30c955f5f941` |
