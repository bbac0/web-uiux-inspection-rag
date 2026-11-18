# guideline_grounded 층: 유형별 근거 조항

정의: 현재 색인된 문서(gov_guide.pdf, gov_check.pdf)에 그 결함을 위반으로 판정할 근거 조항이 있는가 (유형 단위).
후보 판정은 수치 또는 규범이 명시적인 경우에만 `candidate_true`, 판단이 애매하면 `ambiguous`, 조항이 없으면 `false`.
최종 판정은 연구자가 `guideline_grounding_decisions.csv` 의 decision 칸(true/false)에 적는다. 비어 있으면 pending.

## 사전 규칙에 따른 제안 (proposed)

규칙: true 조건: (a) 색인된 문서에 규범형('~한다')으로 쓰인 명시적 조항, (b) 특정 컴포넌트에 한정되지 않은 일반 조항, (c) 주입된 결함이 그 조항을 명백히 위반. '권장' 수준은 해당하지 않음.

| 유형 | 제안(proposed) | 규칙 적용 근거 | 현재 결정 |
|---|---|---|---|
| Poor Contrast Ratio | `true` | (a) gov_guide 122쪽 '이때 명도 대비를 준수하여 시각적 접근성을 확보한다' + 대비율 표(일반 텍스트 AA 4.5:1), (b) 타이포그래피 '글자 색상' 일반 조항, (c) 주입값 1.26:1 은 4.5:1 에 명백히 미달. | true |
| Mobile Layout Breakage | `false` | (b) 불충족: '가로 스크롤 없음'은 첨부파일 패턴(gov_check 182쪽)·패널 컴포넌트(gov_guide 413쪽) 문맥에만 있고 페이지 전체 일반 조항이 없음. | false |
| Button Area Clipping | `false` | (a)·(b) 불충족: 수치 조항은 44×44px '권장'(gov_guide 520쪽), 24px 은 브레드크럼 전용 점검 절차(gov_check 98쪽)와 부록 도구 사용법(269쪽)뿐. '버튼을 적절한 크기로 제공한다'(520쪽)는 규범형이지만 수치 기준이 '권장'이고 버튼 컴포넌트 조항. | false |
| Standard Terminology Violation | `false` | (a) 불충족: 근거 조항 없음 (gov_check 208쪽은 링크 목적지 규정). | false |
| Duplicate ID Markup Error | `false` | (a) 불충족: 근거 조항 없음. | false |

## 이전 단계의 후보 판정 (참고)

| 유형 | 후보 판정 | 이유 |
|---|---|---|
| Poor Contrast Ratio | `candidate_true` | 일반 텍스트 4.5:1 수치 기준과 '명도 대비를 준수한다' 규범이 명시됨. 주입값 1.26:1 은 명백한 미달. |
| Mobile Layout Breakage | `ambiguous` | '가로 스크롤 없음' 기준은 첨부파일 패턴·패널 컴포넌트 같은 특정 문맥에만 명시되어 페이지 전체 규칙인지 애매. |
| Button Area Clipping | `ambiguous` | 44×44px(터치)·17×17px(마우스) 수치가 있으나 '권장'. 24px 타겟 사이즈는 부록 점검 방법. 규범 강도가 애매. |
| Standard Terminology Violation | `false` | 색인된 두 문서에 근거 조항 없음 (사용자 지시로 false 고정). |
| Duplicate ID Markup Error | `false` | 색인된 두 문서에 근거 조항 없음. |

## 근거 조항 후보 표

| 유형 | 조항 원문 요약 | 청크 ID | 파일 | 쪽 | 수치 또는 규범이 명시적인가 |
|---|---|---|---|---:|---|
| Poor Contrast Ratio | 글자 색상은 명도 대비를 준수한다. 일반 텍스트 AA 4.5:1, 큰 텍스트 AA 3:1 (표) | `ff7cefaf-c3e1-4f66-856c-f8b8e24da4ec` | gov_guide.pdf | 122 | 명시적: 수치 기준(4.5:1)과 '준수한다' 규범 |
| Poor Contrast Ratio | 매직넘버 40/50/70/90 = 명도 대비 3:1 / 4.5:1 / 7:1 / 15:1 로 색상 간 구분을 정의 | `0f817b6f-607f-4138-b038-76743de34340` | gov_guide.pdf | 76 | 명시적: 수치 정의 (색상 체계 설명) |
| Poor Contrast Ratio | 접근성을 고려한 대비율: 명도 대비를 준수한다 | `f6cfe97d-7ade-4f9d-b6aa-bf69458d39e0` | gov_guide.pdf | 100 | 규범 명시, 수치는 다른 쪽(122쪽)에 있음 |
| Mobile Layout Breakage | [첨부파일 점검] 화면에 가로 스크롤이 없음, 미준수: 작은 화면 너비에서 화면 자체에 가로 스크롤이 생성되는 경우 (근거: 모바일을 염두에 두고 디자인) | `4536a37e-2033-44f9-913a-fd9fe9ef6fdc` | gov_check.pdf | 182 | 애매: 기준은 명시적이지만 '첨부파일' 기본 패턴의 점검 항목 안에 있어 페이지 전체 일반 규칙인지 불분명 |
| Mobile Layout Breakage | 레이아웃: 화면 크기에 따라 콘텐츠 영역을 유지/축소하는 반응형 그리드 | `3b89f2be-7f01-404e-a43c-840c22c35eae` | gov_guide.pdf | 148 | 애매: 설계 지침(서술), 위반 판정 기준 아님 |
| Mobile Layout Breakage | 브레이크포인트: small 360px 이상, medium 768px 이상, large 1024px 이상 | `4782b967-f132-43c0-bb85-4b3693184c96` | gov_guide.pdf | 153 | 애매: 수치는 있으나 넘침 금지 규범이 아님 |
| Mobile Layout Breakage | [패널 컴포넌트] 패널 영역에 별도의 세로, 가로 스크롤이 생성되어서는 안 된다 | `27829051-5613-42e4-90fd-2507445f9c90` | gov_guide.pdf | 413 | 애매: 특정 컴포넌트 규칙 |
| Button Area Clipping | [버튼] 버튼을 적절한 크기로 제공한다. 마우스 17×17px, 터치 44×44px 이상 '권장' (KWCAG 2.2 조작 가능, WCAG Target Size AAA) | `33a944f1-c266-42bf-bc65-d29b1da48967` | gov_guide.pdf | 520 | 애매: 수치 기준은 명시적이지만 '권장' 수준. 높이 2px·글자 크기 0 버튼은 어떤 수치로도 미달 |
| Button Area Clipping | [부록 도구 활용] 타겟 사이즈: 계산된 height, width 가 모두 24px 이상인지 확인 | `d777af5c-bcd9-4090-94ef-5d5ab2480b0c` | gov_check.pdf | 269 | 애매: 점검 도구 설명(부록), 버튼 컴포넌트 규칙과 직접 연결은 아님 |
| Button Area Clipping | [브레드크럼 13 점검 절차] 브레드크럼 경로 중 가장 짧은 항목의 너비와 높이가 모두 24px 이상임을 확인한다 (근거: 브레드크럼 경로 링크 간 간격을 충분히 제공한다) | `38dfc017-79da-4713-9cfd-a95600243d45` | gov_check.pdf | 98 | 브레드크럼 전용, 점검 절차 문장('확인한다'), 근거 문장은 규범형이나 수치 없음 |
| Button Area Clipping | [크기 토큰] Medium 40px: 주로 버튼, 인풋에 사용 | `645124a6-8e77-4717-aa8d-a751a10e4631` | gov_guide.pdf | 130 | 애매: 디자인 토큰 정의, 위반 판정 기준 아님 |
| Duplicate ID Markup Error | id 값 중복 금지, 마크업 오류(파싱) 방지에 해당하는 조항 없음. 'id 속성'이 나오는 청크는 탭 컴포넌트의 aria-controls 연결 설명(gov_guide 457쪽)과 건너뛰기 링크 점검 방법(gov_check 84쪽)뿐이고, '오류 방지'(gov_guide 141쪽, 터치 오류)와 '중복되지'(gov_guide 291쪽, 스크린리더 정보 중복)는 무관 | - | - | - | 조항 없음 |
| Standard Terminology Violation | '로그인'을 표준 용어로 정하거나 '접속하기' 등 변형 표현을 금지하는 조항 없음 (oracle_candidates.md 맨 앞 요약, terminology_basis.py) | - | - | - | 조항 없음 |

## 원문 (해당 문구 주변)

**Poor Contrast Ratio** — `ff7cefaf-c3e1-4f66-856c-f8b8e24da4ec` gov_guide.pdf 122쪽

```text
본문에서는 주로 그레이 계열을 유지하며, 주요 동작에는 primary, secondary, point, system 색상을 사용할 수 있다. 이때 명도 대비를 준수하여 시각적 접근성을 확보한다. 등급 큰 텍스트 일반 텍스트 대비율 AA 3:1 (매직넘버: 40) 4.5:1 (매직넘버: 50) 최소 AAA 4.5:1 (매직넘버: 50) 7:1 (매직넘버: 70) 강화 텍스트 크기 pt(point) 단위 px(pixel) 단위 큰 텍스트 18pt 이상, 굵게 표시된 경우 최소 14pt 이상 24px 이상, 굵게 표시된 경우 최소 18.66px 이상 일반 텍스트 18pt 이하, 굵게 표시된 경우 14pt 미만 24px 이하, 굵게 표시된 경우 18.66px 미만
```

**Poor Contrast Ratio** — `0f817b6f-607f-4138-b038-76743de34340` gov_guide.pdf 76쪽

```text
단계 간의 차이를 수치화하여 WCAG 기준에 따른 명도 대비를 쉽게 계산할 수 있게 도와준다. 정보 전달에 필요한 글자, 배경, 그래픽 등의 요소 간의 주요 명도 대비 비율을 정의하여 색상 간 시각적 구분을 명확히 한다. • 매직넘버 40 ㏂ 명도 대비 3:1 • 매직넘버 50 ㏂ 명도 대비 4.5:1 • 매직넘버 70 ㏂ 명도 대비 7:1 • 매직넘버 90 ㏂ 명도 대비 15:1 ㅇ
```

**Poor Contrast Ratio** — `f6cfe97d-7ade-4f9d-b6aa-bf69458d39e0` gov_guide.pdf 100쪽

```text
디지털 정부서비스 UI/UX 가이드라인 | 디자인 스타일 / 색상 100 주요 색상 사용 주요 액션이나 중요한 정보를 강조하는 데 사용한다. 모범 사례 피해야 할 사례 접근성 고려한 대비율 명도 대비를 준수한다. 모범 사례 피해야 할 사례
```

**Mobile Layout Breakage** — `4536a37e-2033-44f9-913a-fd9fe9ef6fdc` gov_check.pdf 182쪽

```text
3. 준수 기준 다. 기본 패턴 - 182 - 3)첨부파일 ②화면에 가로 스크롤이 없음③그룹화된 입력/선택 관련 컴포넌트 간 관계를 파악할 수 있음◦하나의 정보를 입력하는 데 필요한 여러 개의 컴포넌트◦의미적으로 관련된 컴포넌트 등* 화면 너비에 따른 콘텐츠 표현 확인하기준수•1, 2를 충족함 미준수 사례•작은 화면 너비에서 콘텐츠가 잘려서 표시되는 경우•작은 화면 너비에서 화면 자체에 가로 스크롤이 생성되는 경우•그룹화된 항목의 레이아웃이 변경되어 요소 간 관계를 이해할 수 없는 경우근거 가이드라인(플랫폼) 모바일을 염두에 두
```

**Mobile Layout Breakage** — `3b89f2be-7f01-404e-a43c-840c22c35eae` gov_guide.pdf 148쪽

```text
디자인 스타일 / 레이아웃 148 표준형 스타일의 경우 㥗 스크린 마진(24px) + 콘텐츠 너비(1200px) > 디바이스 1248px: 콘텐츠 영역 유지 㥗 스크린 마진(24px) + 콘텐츠 너비(1200px) < 디바이스 1248px: 콘텐츠 영역 축소 풀 반응형 그리드/ 유연한 콘텐츠 영역 (가변형) 화면 크기에 따라 유동적으로 변화하여 다양한 기기에서 최적의 레이아웃을 제공한다. 큰 화면에서 콘텐츠 영역이 지나치게 넓어지지 않도록 가독성과 정보 전달력을 고려하여 레이아웃을 조정한다 ㏂ ㏂
```

**Mobile Layout Breakage** — `4782b967-f132-43c0-bb85-4b3693184c96` gov_guide.pdf 153쪽

```text
격을 줄여야 화면 공간을 효율적으로 사용할 수 있다. 표준형 스타일은 PC와 모바일 두 가지 주요 디바이스 유형에 대한 간격을 설정하며, 레이아웃 간격이나, 텍스트 사이의 간격, 카드 내부 패딩값 등을 제공한다. 모드 범위 뷰포트 기준 사이즈 (콘텐츠 영역) 사용 Mobile small 360px 이상 348px 태블릿을 포함한 소형 디바이스에 지원medium 768px 이상 PC large 1024px 이상 1200px 일반적으로 데스크탑 및 대형 화면을 지원xlarge 1280px 이상
```

**Mobile Layout Breakage** — `27829051-5613-42e4-90fd-2507445f9c90` gov_guide.pdf 413쪽

```text
디지털 정부서비스 UI/UX 가이드라인 | 컴포넌트 / 레이아웃·표현 / 아코디언 413 05 패널 영역에 스크롤이 발생하지 않도록 한다. 패널 내부 콘텐츠가 길어져 화면의 뷰포트를 넘어가는 경우, 화면 스크롤을 통해 콘텐츠를 탐색할 수 있어야 한다. 패널 영역에 별도의 세로, 가로 스크롤이 생성되어서는 안 된다. [피해야 할 사례] 기관을 방문하려면 어떻게 해야 하나요? 부서별 업무 또는 직원별 연락처는 어디에서 확인할 수 있나요? 문의사항은 어디에서 확인할 수 있나요? 사용성 가이드라인
```

**Button Area Clipping** — `33a944f1-c266-42bf-bc65-d29b1da48967` gov_guide.pdf 520쪽

```text
디지털 정부서비스 UI/UX 가이드라인 | 컴포넌트 / 액션 / 버튼 520 접근성 가이드라인 07 버튼을 적절한 크기로 제공한다. 클릭, 터치 영역을 정교하게 조작하기 어려운 사용자를 고려하여, 마우스 상호작용에 대해서는 17px × 17px, 터치 상호작용에 대해서는 44px x 44px 이상의 영역에서 반응할 수 있는 컨트롤 크기를 사용할 것을 권장한다. ㏂ KWCAG 2.2 조작 가능 ㏂ WCAG 2.1 Target Size (AAA)
```

**Button Area Clipping** — `d777af5c-bcd9-4090-94ef-5d5ab2480b0c` gov_check.pdf 269쪽

```text
부록 가. 도구 활용방법 - 269 - 나)타겟 사이즈(Target size) 및 간격 점검하기타겟 사이즈 확인1.크롬에서 개발자 도구를 연다.2.Inspector mode(검사기 모드; )로 점검을 원하는 요소를 클릭한다.3.Computed Tab(계산됨 탭)의 <height>, <width> 값이 모두 24px 이상으로 제공되는지 확인한다. 타겟 사이즈의 크기가 24px을 충족하지 못할 경우1.크롬 확장 프로그램을 설치한다.
```

**Button Area Clipping** — `38dfc017-79da-4713-9cfd-a95600243d45` gov_check.pdf 98쪽

```text
크럼을 본문 오른쪽 상단에 제공한 경우•브레드크럼을 사이드 메뉴 상단에 제공한 경우근거 가이드라인(사용성) 브레드크럼은 항상 본문 제목의 왼쪽 상단에 표시한다. [브레드크럼 13]브레드크럼 링크 간 간격을 충분히 제공하고 있다.점검화면/요소‣브레드크럼 점검절차/방법1.브레드크럼 경로 중 가장 짧은 항목의 너비와 높이가 모두 24px 이상임을 확인한다.*2.#1에 해당하지 않는 경우, 각 경로 요소 중심부에 24px CSS 직격 크기를 가진 원을 그려 서로 중첩되지 않음을 확인한다.*** 스타일 속성 점검하기(너비 및 높이)** 타겟 사이즈(Target size) 및 간격 점검하기준수•1을 충족함•또는 2를 충족함미준수 사례•브레드크럼 항목 간 간격이 충분하지 않은 경우근거 가이드라인(사용성) 브레드크럼 경로 링크 간 간격을 충분히 제공한다. [브레드크럼 14]
```

**Button Area Clipping** — `645124a6-8e77-4717-aa8d-a751a10e4631` gov_guide.pdf 130쪽

```text
x 16*16 2px Small 태그, 칩 같은 작은 컴포넌트에서 사용한다. 20*20 4px Chips Checkbox Radio button Switch Tag 24*24 4px 32*32 4px Medium 기본이 되는 값으로 주로 버튼, 인풋 등에서 사용한다. 40*40 6px Button Text input Textarea Select Carousel-Number Step indicator Pagination 48*48 6px 56*56 6px 64*64 6px Large 주로 카드와 같은 큰 컴포넌트에 사용한다. 72*72 10px Card Dialog 80*80 10px Xlarge 가장 큰 값으로 주로 배너, 바텀 시트 같은 화면을 차지하는 비율이 큰 컴포넌트에 사용한다. 96*96 12px Banner Dialog Bo
```

(이 문서는 `experiments/revision/guideline_grounding.py` 가 만든다.)
