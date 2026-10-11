# Meaningful integrity, timing, model-rank and numerical-reproduction checks.
entry <- sub("^--file=", "", commandArgs(FALSE)[grepl("^--file=", commandArgs(FALSE))][1])
source(file.path(dirname(normalizePath(entry)), "common.R"))
checks <- list()
check <- function(name, condition, detail) {
  if (!isTRUE(condition)) stop(name, ": ", paste(detail, collapse = ", "))
  checks[[length(checks) + 1L]] <<- list(check = name, passed = TRUE, detail = detail)
}
S <- read_json(file.path(OUT, "summary.json"))
finite <- function(x) {
  if (is.list(x)) return(all(vapply(x, finite, logical(1))))
  if (is.numeric(x)) return(all(is.finite(x)))
  TRUE
}
check("Reported numeric results are finite", finite(S), "No NaN or infinity in summary.json")
games <- read_csv_gz(file.path(CLEAN, "unique_games.csv.gz"))
focal <- read_csv_gz(file.path(CLEAN, "focal_games.csv.gz"))
panel <- fread(file.path(CLEAN, "primary_player_pool_week.csv"))
rm <- read_csv_gz(file.path(CLEAN, "adjacent_rematches.csv.gz"))
check("Unique game IDs", !anyDuplicated(games$game_id), nrow(games))
check("Valid results", all(games$white_score %in% c(0, .5, 1)), as.list(sort(unique(games$white_score))))
check("Valid speed pools", all(games$time_class %in% c("bullet", "blitz", "rapid")), as.list(sort(unique(games$time_class))))
check("Focal references valid", all(focal$game_id %in% games$game_id), nrow(focal))
check("One or two focal records per game", all(focal[, .N, by = game_id]$N %in% c(1L, 2L)), "One row per sampled participant")
check("Focal account-game IDs unique", !anyDuplicated(focal[, .(game_id, player)]), "No participant duplication")
check("PGN and JSON ratings agree", all(games$pgn_rating_match), "Matches documented post-game values")
check("Primary panel supports contrast", all(panel$event_week != 0) && all(panel$n_games >= 3) && uniqueN(panel$player) >= 3,
  list(players = uniqueN(panel$player), cells = nrow(panel)))
support <- panel[, .(support = uniqueN(paste(pool, post))), by = player]
check("Participants observed in both pools and periods", all(support$support == 4L), nrow(support))
X <- model.matrix(~factor(unit) + factor(event_week) + treat, data = panel)
check("Primary design has full rank", qr(X)$rank == ncol(X), list(columns = ncol(X), rank = qr(X)$rank))
fit <- lm(rating ~ factor(unit) + factor(event_week) + treat, data = panel)
robust <- coefficient_table(fit, panel$player)[term == "treat"]
check("Saved DiD coefficient and interval reproduce", max(abs(c(robust$coefficient - S$primary$estimate,
  robust$se - S$primary$se, robust$ci_low - S$primary$ci_low, robust$ci_high - S$primary$ci_high))) < 1e-7, "Independent refit of saved primary panel")
reference <- read_json(file.path(ROOT, "data", "reference_estimates.json"))
fields <- c("estimate", "se", "ci_low", "ci_high", "pvalue")
differences <- vapply(fields, function(field) abs(S$primary[[field]] - reference$primary[[field]]), numeric(1))
check("Primary regression matches validated reference", max(differences) < 1e-7, list(max_absolute_difference = max(differences)))
observed_specs <- setNames(S$specifications, vapply(S$specifications, function(x) x$specification, character(1)))
spec_difference <- 0
for (expected in reference$specifications) {
  current <- observed_specs[[expected$specification]]
  stopifnot(!is.null(current))
  spec_difference <- max(spec_difference, vapply(fields, function(field) abs(current[[field]] - expected[[field]]), numeric(1)))
}
check("All sensitivity regressions match reference", spec_difference < 1e-7, list(specifications = length(reference$specifications), max_absolute_difference = spec_difference))
check("Joint pretrend test matches reference", abs(S$pretrend_p - reference$pretrend_p) < 1e-7, S$pretrend_p)
outcome_fields <- c("gap100", "post_interaction", "post_interaction_p")
check("Outcome regression matches reference", max(vapply(outcome_fields, function(field) abs(S$outcome[[field]] - reference$outcome[[field]]), numeric(1))) < 1e-7,
  list(decisive_games = S$outcome$n, pairs = S$outcome$pairs))
count_fields <- c("archive_records", "rejected_archive_rows", "unique_games", "focal_observations", "deduplicated_eligible_rows")
check("Raw reconstruction matches reference counts", all(vapply(count_fields, function(field) S$audit[[field]] == reference$audit[[field]], logical(1))), "Same games, exclusions and focal observations")
check("Rematch audit nonempty", nrow(rm) > 100, list(games = nrow(rm), pairs = uniqueN(rm$pair)))
check("Prior information predates game start", all(rm$start_stamp >= rm$prior_end_time) && all(rm$rematch_gap_seconds >= 0 & rm$rematch_gap_seconds <= 300), "Maximum start gap 300 seconds")
check("Prior rematch is latest observed for both", all(rm$prior_observed_white == rm$prior_end_time & rm$prior_observed_black == rm$prior_end_time), "Checks observed histories, not unseen games")
hashed <- 0L; unavailable <- 0L
for (line in readLines(file.path(ROOT, "data", "request_log.jsonl"), warn = FALSE)) {
  item <- fromJSON(line)
  if (item$status %in% c(404L, 410L)) {unavailable <- unavailable + 1L; next}
  con <- gzfile(file.path(ROOT, item$file), "rb")
  bytes <- readBin(con, "raw", n = 1e8); close(con)
  stopifnot(identical(digest::digest(bytes, algo = "sha256", serialize = FALSE), item$sha256_uncompressed))
  hashed <- hashed + 1L
}
check("Frozen response hashes match", hashed > 0L, list(checked = hashed, unavailable_archives = unavailable))
figures <- list.files(FIG, pattern = "\\.pdf$", full.names = TRUE)
check("All publication figures exist", length(figures) == 13L, "13 vector PDF figures")
check("All raster previews exist", all(file.exists(sub("\\.pdf$", ".png", figures))), length(figures))
check("Summary counts match data", nrow(games) == S$audit$unique_games && nrow(focal) == S$audit$focal_observations,
  list(unique_games = nrow(games), focal_rows = nrow(focal)))
write_json(list(checks = checks, all_passed = TRUE, scope = "Integrity, observed-history timing, design rank and saved-result reproduction; does not establish causal identification."), file.path(OUT, "verification.json"))
message("All ", length(checks), " R verification checks passed.")
