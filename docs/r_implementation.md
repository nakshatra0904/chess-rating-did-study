# My R implementation and numerical checks

I implemented the full pipeline in R: serial PubAPI collection, parsing and cleaning,
player-pool-week aggregation, fixed-effects DiD and event study, placebo regressions,
paired-account bootstrap contrasts, participation summaries, binomial outcome
regression, adjacent-rematch measurement audit, all 13 figures and the LaTeX report.

I compared deterministic estimates against the independently validated frozen-study
reference values. The primary DiD, its account-clustered CR1 standard error and
interval, the joint pretrend test and the retrospective regression coefficients
agree to numerical precision. I retain these reference values for ongoing checks.

I recomputed the bootstrap intervals using R's random-number generator rather than
reusing the earlier intervals. I record the seed, settings and resampling count in
summary.json. This changes small Monte Carlo details but preserves the estimates
and interpretation. Bootstrap intervals and regression intervals describe different
estimands and sampling uncertainty; neither resolves causal identification.

The project uses native R scripts and an optional R Markdown notebook. No other
programming-language runtime is needed for the analysis or report-source generation.
LaTeX compilation requires a TeX compiler separately.
