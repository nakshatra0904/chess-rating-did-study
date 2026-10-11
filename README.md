# Rating shifts without identified skill shifts

I study Chess.com's 10 September 2020 rating reform using difference-in-differences (DiD), an event study, placebo breaks, descriptive statistics and regression analysis.

Research and analysis by **nakshatra0904**.

## Start here

- Read [the compiled report](report/report.pdf).
- Inspect [the LaTeX source](report/report.tex).
- See [all estimates and metadata](results/summary.json).
- Use [the related-work and search ledger](docs/related_work.md) to evaluate the research question.

## Main question

How much does the apparent effect of a rating rebase depend on the comparison pool, participant support, weighting, and information timing?

The reform announced +150 bullet points and moved 10|0 games from blitz to rapid. Earlier work already covers cross-rating prediction and post-game leakage. I conduct a narrower empirical sensitivity audit, not a claim of worldwide first discovery.

## Difference-in-differences technique

I treat bullet as the affected rating pool and compare it with blitz for the same players around 10 September 2020, excluding the rollout week. I estimate player-by-pool and event-week fixed effects, with standard errors clustered by player. I also examine event-study leads, four pre-period placebo breaks and alternative controls and weights.

The treatment coefficient measures the change in bullet relative to the contemporaneous change in blitz. A causal interpretation requires untreated parallel trends, limited spillovers and stable observation. Blitz was also affected by the reform, so these assumptions remain contestable. I do not use RDD because no credible account-level assignment threshold is observed.

See report Sections 5 and 7, results/did_specifications.csv and results/event_study.csv.

## Actual data and principal findings

- 61,479 unique rated standard games, June-October 2020.
- 62,181 focal account-game rows from 120 July-active accounts.
- 256 deterministically sampled current-GM accounts screened from a 1743-account frozen frame.
- My primary two-way fixed-effects DiD estimate: 191.6 points, exploratory 95% player-clustered interval [99.6, 283.6]; 20 player clusters.
- Directly excluding 10|0 changes the estimate by only about 0.02 points in this cohort; game-count weighting changes it from about 191.6 to 261.1 points.
- Same adjacent-rematch games: post-game rating information gives about 68.0% apparent accuracy versus 60.0% using prior-rematch ratings under a fixed probability mapping.

I interpret the DiD contrast conditionally rather than as an identified causal improvement in skill. There is one site-wide event, an affected comparator pool, uncertain actual treatment receipt, and a selected cohort. All estimates, exploratory tests and limitations are in the report.

## Rebuild from frozen data (no API credentials)

I used Python 3.12. From this repository's root:

```text
python -m venv .venv
```

Activate the environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux), then:

```text
python -m pip install -r requirements.txt
python scripts/analyze.py
python scripts/verify.py
python scripts/build_report.py
```

Compile the LaTeX source from the report directory:

```text
cd report
tectonic report.tex --keep-logs
```

Alternatively, run `xelatex -interaction=nonstopmode -halt-on-error report.tex` twice. The source uses portable TeX Palatino/Helvetica/Courier fonts and 13 vector PDF figures. Tectonic 0.17.0 compiled the delivered PDF. Install a TeX compiler separately; compiler binaries and downloaded Python libraries are intentionally excluded from the repository.

## Optional fresh collection

```text
python scripts/collect_data.py --n 256
```

The collector uses serial requests, a recognizable user agent, caching and retries. The frozen frame is reused if present. To create a genuinely fresh contemporary frame, use a separate working copy; never overwrite the frozen data without preserving its provenance. Current title membership and mutable archives mean fresh data may not reproduce this cohort. There is one recorded unavailable archive; it is not imputed.

## Files

- `data/raw/`: individually gzip-compressed complete public API responses, including PGN; the sampling frame is frozen.
- `data/cohort.json`: exact screening rules, selected names and active accounts.
- `data/request_log.jsonl`: successful-response SHA-256 hashes, URLs, timestamps and error records.
- `data/processed/`: unique games, focal games, primary weekly panel and observed adjacent rematches.
- `results/`: descriptive statistics, model coefficients, event study, placebo dates, paired contrasts, measurement metrics and verification.
- `report/`: actual LaTeX source, compiled PDF and vector/raster figures.
- `scripts/`: collection, analysis, report generation and meaningful verification.
- `docs/`: related-work search ledger and data attribution.
- `notebooks/`: optional result exploration notebook; execution is not required to reproduce the report.

## Repository and complete project

Repository: https://github.com/nakshatra0904/chess-rating-did-study

I include the entire analysis as ordinary repository files: frozen data, source code, numerical outputs, graphs, LaTeX and the compiled report. Every individual file is below GitHub's 100 MiB file limit. The accompanying ZIP contains the same project for offline use.

## Provenance, limitations and licensing

Public Chess.com PubAPI data are attributed to Chess.com. The source data are not covered by this project's MIT code license. Do not infer rights over platform branding, protected content, or third-party work. No private account data or credentials are included. Current GM-account sampling is a historical survivor sample and may include accounts titled only after 2020. Generalization is limited to the described cohort.

I prepared this project on 11 October 2026. See the report bibliography for primary sources and the search ledger for novelty limits.
