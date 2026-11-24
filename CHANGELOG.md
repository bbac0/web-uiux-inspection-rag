# Changelog

## v4.3

- Site-level mean in merge_results() now uses rounding instead of integer division. No effect on any reported metric; all reported experiments (v4.2) analysed one page per run, so the site-level score equals the page-level score.
- services/analyzer.py differs from the freeze manifest (freeze v5) in these three lines only; the manifest and the exp-freeze-v5 tag are unchanged and document the evaluated version.
- Verified: for single-page runs (n=1) the result is identical for all 200 stored E1-R1 page results; for n=2-5 the site-level score differs by 0 or +1.
