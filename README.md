# Rating shifts without identified skill shifts

I study Chess.com's 10 September 2020 rating reform using **R**, difference-in-differences (DiD), an event study, placebo breaks, descriptive statistics and regression analysis.

Research and analysis by **nakshatra0904**. Public repository: https://github.com/nakshatra0904/chess-rating-did-study .

## Start here

- Read [my compiled LaTeX report](report/report.pdf).
- Inspect [the LaTeX source](report/report.tex).
- Run [my full R analysis](scripts/analyze.R).
- See [all estimates and metadata](results/summary.json).
- Read [the earlier-work and search ledger](docs/related_work.md).

## Main question and earlier work

How much does the apparent effect of a rating rebase depend on the comparison pool, participant support, weighting, and information timing?

The reform announced +150 bullet points and moved 10|0 games from blitz to rapid. I found earlier work on cross-rating prediction and post-game leakage, so I focus on comparator sensitivity, participation and weighting around the actual reform. My targeted search supports a narrower empirical contribution; it does not prove worldwide novelty.

## Difference-in-differences technique

I treat bullet as the affected rating pool and compare it with blitz for the same players around 10 September 2020. I exclude the rollout week and estimate player-by-pool and event-week fixed effects. I calculate account-clustered CR1 sandwich standard errors, using the correction G/(G-1) * (N-1)/(N-K) and Student-t intervals with G-1 degrees of freedom. The R implementation exposes this calculation in [scripts/common.R](scripts/common.R).

I also examine event-study leads, four pre-period placebo breaks, alternative comparators and sample support, weighting, a differential linear trend, paired-player bootstrap contrasts, and a pair-clustered logistic regression.

The DiD coefficient measures bullet's change relative to blitz's contemporaneous change. A causal interpretation requires untreated parallel trends, limited spillovers and stable observation. Blitz was also affected by the reform, so these assumptions remain contestable. I do not use RDD because no credible account-level assignment threshold is observed.

See report Sections 5 and 7, [DiD estimates](results/did_specifications.csv), [the event study](results/event_study.csv) and [placebo breaks](results/placebo_dates.csv).

## Actual data and principal findings

- 61,479 unique rated standard games, June-October 2020.
- 62,181 focal account-game observations from 120 July-active accounts.
- 256 deterministically sampled current-GM accounts screened from a 1,743-account frozen frame.
- My primary DiD estimate: **191.6 points**, exploratory 95% account-clustered interval **[99.6, 283.6]**; 20 account clusters and 485 cells.
- Excluding 10|0 changes the estimate by about 0.02 points in this cohort. Game-count weighting changes it from about 191.6 to 261.1 points.
- In the same adjacent rematches, post-game rating information gives about 68.0% apparent accuracy versus 60.0% using prior-rematch ratings under a fixed probability mapping.

I interpret these results conditionally. They do not establish a causal improvement in latent chess skill. There is one site-wide event, an affected comparator, uncertain actual treatment receipt, and a selected cohort.

## Reproduce my analysis entirely in R

I used **R 4.5.1**. Exact package versions and their dependencies are recorded in [renv.lock](renv.lock); `DESCRIPTION` lists the core packages. From the repository root:

```text
# Run these commands in a terminal, or open the scripts in RStudio.
Rscript scripts/setup.R
Rscript scripts/analyze.R
Rscript scripts/verify.R
Rscript scripts/build_report.R
```

The first command restores packages into an ignored project-local `.R-library` folder. The full analysis rebuilds processed data, all numerical outputs and all **13 vector PDF figures and PNG previews** directly from the frozen raw archives. I require no API credentials or fresh collection for reproduction. The verification script checks raw-response hashes, unique games, timing, model rank and reproduction of the saved and reference estimates. [My session information](results/session_info.txt) records the environment used for this release.

I use 10,000 bootstrap resamples with seed 20201011 and R's Mersenne-Twister / Inversion / Rejection settings. The bootstrap intervals were recomputed in R. An identical seed across different software does not imply identical random draws. The deterministic regression coefficients, clustered intervals, event-study test and sample counts reproduce the earlier validated estimates to numerical precision.

## Compile the LaTeX report

After generating the report source, compile from the report folder:

```text
cd report
tectonic report.tex --keep-logs
```

Alternatively, run `xelatex -interaction=nonstopmode -halt-on-error report.tex` twice. I compiled the delivered PDF with Tectonic 0.17.0. Portable TeX fonts and vector figures are included. A TeX compiler must be installed separately.

## Optional fresh public-data collection

```text
Rscript scripts/collect_data.R --n 256
```

I use serial requests, a recognizable user agent, cached responses and retries. The frozen sampling frame is reused while it exists. Use a separate copy for a contemporary frame rather than overwriting historical provenance. Title membership and mutable archives can change. I log unavailable archives and do not impute their games.

## Files

- `scripts/`: native R collection, cleaning, analysis, inference, figure generation, verification, package restoration and report generation.
- `data/raw/`: complete public API responses, individually gzip-compressed, including PGN and the frozen title frame.
- `data/cohort.json`: the deterministic sample and activity-screening rules.
- `data/request_log.jsonl`: URLs, UTC retrieval times, status codes and uncompressed-response SHA-256 hashes.
- `data/processed/`: unique games, focal observations, primary weekly panel and observed adjacent rematches.
- `data/reference_estimates.json`: independently validated numerical reference values for regression-reproduction checks.
- `results/`: descriptive statistics, model estimates, event study, placebo breaks, measurement metrics, verification and session information.
- `report/`: LaTeX source, compiled PDF, and every graph in PDF and PNG.
- `docs/`: earlier work, search queries and data attribution.
- `notebooks/explore_results.Rmd`: optional R exploration notebook; rendering it additionally requires `rmarkdown` and `knitr`.
- `.github/workflows/verify.yml`: automated reproduction and verification of the R pipeline.

## Complete downloads

I provide the revised report and a complete project ZIP in the [R release](https://github.com/nakshatra0904/chess-rating-did-study/releases/tag/v2.0.0). Ordinary repository files contain the complete project as well. Every individual file is below GitHub's 100 MiB file limit.

## Provenance, limitations and licensing

I attribute the public PubAPI data to Chess.com. My MIT license covers the original code and report text, and does not relicense platform data or third-party works. Current-GM sampling is a historical survivor sample and may include accounts titled only after 2020; the results do not describe all platform users. Source citations and the bounded novelty claim remain in the report and documentation.

I prepared the original study on 11 October 2026 and revised this R edition on 12 October 2026.
