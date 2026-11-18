# Draft: Section 5.3 — provenance fields in the archived run (English, for revision)

Source table: `results/revision/e8_run2_reanalysis.md`, section "(v-d) 5.3절 확정 표: 정의 C" (final; numbers in
`results/revision/e8_definition_c.csv`). Scope: the 502 issues that the archived second run (run2) reported for the
test pages themselves; issues reported for the linked `/login` error page are excluded.

---

We examined the provenance fields (`source_file`, `page_number`) of the 502 issues that the archived run reported for the
200 test pages, excluding issues reported for pages reached by the crawler. Because the vector store queried in that run
was empty, every retrieval returned zero chunks, so none of these citations could have been grounded in retrieved
guideline text. The source file was missing in 38 issues (7.6%; 17 null values, 19 "N/A", and 2 empty strings). In 81
issues (16.1%), the citation reproduced the example values given in the prompt's output template verbatim
(`gov_guide.pdf` with page `[12]` or `[12, 13]`). Of the 464 issues that named a source file, 92 (19.8%) named a document
that is not part of the indexed corpus, such as "General Web Standards" or "정부 표준 가이드라인" (18.3% of all 502 issues;
25.9% when missing values are counted together with these names). No issue cited `gov_check.pdf`, the second document in
the corpus. Taken together, these fields in the archived run reflect the prompt template and the model's prior rather
than retrieved evidence, and they should not be read as citations of the guideline.

---

Notes for the authors (not for the manuscript):
- "Indexed corpus" = `gov_guide.pdf` and `gov_check.pdf` (1,020 chunks in `services/chroma_db`).
- File names were not normalised (e.g. "General Web Standards" and "General web standards" are counted as written).
- The numbers above are fixed; if the definition changes, recompute with `experiments/revision/e8_definition_c.py`.
