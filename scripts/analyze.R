# I rebuild the complete analysis and all 13 figures from the frozen archives.
entry <- sub("^--file=", "", commandArgs(FALSE)[grepl("^--file=", commandArgs(FALSE))][1])
source(file.path(dirname(normalizePath(entry)), "common.R"))
source(file.path(ROOT, "scripts", "extract_data.R"))

panel <- function(focal, control = "all", minimum = 3L, balanced = TRUE, window = NULL) {
  bullet <- copy(focal[time_class == "bullet"]); bullet[, pool := "bullet"]
  comparator <- copy(focal[time_class == "blitz"])
  if (control == "no600") comparator <- comparator[time_control != "600"]
  if (control %in% c("180", "300")) comparator <- comparator[time_control == control]
  comparator[, pool := "control"]
  a <- rbindlist(list(bullet, comparator)); a <- a[event_week != 0L]
  if (!is.null(window)) a <- a[abs(event_week) <= window]
  pp <- a[, .(rating = mean(rating), n_games = .N, score = mean(score)), by = .(player, pool, event_week)]
  pp <- pp[n_games >= minimum]
  pp[, `:=`(post = as.integer(event_week >= 1L), bullet = as.integer(pool == "bullet"))]
  if (balanced) {
    good <- pp[, .(support = uniqueN(paste(pool, post))), by = player][support == 4L, player]
    pp <- pp[player %in% good]
  }
  pp[, `:=`(unit = paste(player, pool, sep = "|"), treat = bullet * post)]
  setorder(pp, player, pool, event_week); pp
}
did <- function(pp, name, trend = FALSE, weighted = FALSE) {
  if (nrow(pp) == 0L || uniqueN(pp$player) < 3L) return(NULL)
  formula <- rating ~ factor(unit) + factor(event_week) + treat
  if (trend) formula <- update(formula, . ~ . + bullet:event_week)
  w <- if (weighted) pp$n_games else rep(1, nrow(pp))
  fit <- lm(formula, data = pp, weights = w)
  tab <- coefficient_table(fit, pp$player)[term == "treat"]
  list(row = data.table(specification = name, estimate = tab$coefficient, se = tab$se,
    ci_low = tab$ci_low, ci_high = tab$ci_high, pvalue = tab$pvalue,
    n_cells = nrow(pp), n_players = uniqueN(pp$player), r_squared = summary(fit)$r.squared), fit = fit)
}
eventstudy <- function(pp) {
  a <- copy(pp); weeks <- sort(unique(a$event_week)); terms <- character(); term_weeks <- integer()
  for (k in weeks[weeks != -1L]) {
    name <- paste0(if (k < 0) "event_m" else "event_p", abs(k))
    a[, (name) := as.integer(event_week == k & bullet == 1L)]
    terms <- c(terms, name); term_weeks <- c(term_weeks, k)
  }
  fit <- lm(as.formula(paste("rating ~ factor(unit) + factor(event_week) +", paste(terms, collapse = " + "))), data = a)
  robust <- cluster_vcov(fit, a$player); tab <- coefficient_table(fit, a$player)
  events <- rbindlist(lapply(seq_along(terms), function(i) {
    t <- tab[term == terms[i]]
    data.table(event_week = term_weeks[i], estimate = t$coefficient, se = t$se, ci_low = t$ci_low, ci_high = t$ci_high)
  }))
  events <- rbind(events, data.table(event_week = -1L, estimate = 0, se = 0, ci_low = 0, ci_high = 0)); setorder(events, event_week)
  pre <- terms[term_weeks >= -6 & term_weeks < -1]
  b <- coef(fit)[pre]; V <- robust$vcov[pre, pre, drop = FALSE]
  statistic <- as.numeric(t(b) %*% solve(V, b)) / length(pre)
  list(events = events, pretrend_p = pf(statistic, length(pre), robust$df, lower.tail = FALSE))
}
probability <- function(gap) 1 / (1 + 10^(-gap / 400))
bootstrap_mean <- function(values, B = 10000L) {
  # Resample complete account or pair contrasts, rather than individual games.
  replicate(B, mean(sample(values, length(values), replace = TRUE)))
}

raw <- extract_data(); games <- raw$games; focal <- raw$focal
S <- list(audit = raw$audit)
desc <- focal[, .(observations = .N, players = uniqueN(player), mean_rating = mean(rating),
  median_rating = median(rating), sd_rating = sd(rating), p10_rating = quantile(rating, .1),
  p90_rating = quantile(rating, .9), mean_score = mean(score)), by = time_class]
setorder(desc, time_class); output(desc, "descriptive_by_pool"); S$descriptive <- records(desc)
phase <- focal[, .(n = .N, players = uniqueN(player), mean = mean(rating), median = median(rating), score = mean(score)),
  by = .(time_class, phase = ifelse(post == 1L, "post", "pre"))]
setorder(phase, time_class, phase); output(phase, "pre_post")
counts <- focal[, .(n = .N), by = .(event_week, time_class)]
counts[, share := 100 * n / sum(n), by = event_week]
activity <- ggplot(counts, aes(event_week, n, color = time_class)) + geom_line() +
  geom_vline(xintercept = 0, linetype = 2) + scale_color_manual(values = COLORS) +
  labs(title = "Weekly activity by rating pool", x = "Event week (10 Sep 2020 = 0)", y = "Focal game observations", color = NULL)
shares <- ggplot(counts, aes(event_week, share, color = time_class)) + geom_line() +
  geom_vline(xintercept = 0, linetype = 2) + scale_color_manual(values = COLORS) +
  labs(title = "Pool composition of observed activity", x = "Event week", y = "Share of focal observations (%)", color = NULL)
save_multi(list(activity, shares), "01_activity", 11, 4.5)
dist <- copy(focal); dist[, phase := factor(ifelse(post == 1, "On / after 10 Sep", "Before 10 Sep"), levels = c("Before 10 Sep", "On / after 10 Sep"))]
hist <- ggplot(dist, aes(rating, after_stat(density), color = phase)) +
  geom_freqpoly(breaks = seq(1000, 3600, 100), linewidth = .8) + facet_wrap(~time_class, nrow = 1) +
  labs(x = "Published post-game rating", y = "Probability density", color = NULL) +
  scale_color_manual(values = c("#256b91", "#b35828"))
save_figure(hist, "02_distributions", 11, 4)
weekly <- focal[, .(rating = mean(rating)), by = .(player, time_class, event_week)]
trends <- weekly[, .(rating = mean(rating)), by = .(time_class, event_week)]
plot <- ggplot(trends, aes(event_week, rating, color = time_class)) + geom_line() + geom_point(size = 1.5) +
  geom_vline(xintercept = 0, linetype = 2) + scale_color_manual(values = COLORS) +
  labs(title = "Mean rating with equal weight for each active player-week", x = "Event week", y = "Published post-game rating", color = NULL)
save_figure(plot, "03_rating_trends", 9, 4.5)

settings <- list(
  list("All blitz; balanced; >=3 games", "all", 3L, TRUE, NULL, FALSE, FALSE),
  list("Exclude 10|0; balanced; >=3 games", "no600", 3L, TRUE, NULL, FALSE, FALSE),
  list("3|0 only; balanced; >=3 games", "180", 3L, TRUE, NULL, FALSE, FALSE),
  list("5|0 only; balanced; >=3 games", "300", 3L, TRUE, NULL, FALSE, FALSE),
  list("All blitz; unbalanced; >=3 games", "all", 3L, FALSE, NULL, FALSE, FALSE),
  list("All blitz; balanced; >=1 game", "all", 1L, TRUE, NULL, FALSE, FALSE),
  list("All blitz; balanced; +/-6 weeks", "all", 3L, TRUE, 6L, FALSE, FALSE),
  list("All blitz; differential linear trend", "all", 3L, TRUE, NULL, TRUE, FALSE),
  list("All blitz; game-count weighted", "all", 3L, TRUE, NULL, FALSE, TRUE))
specs <- list(); primary <- NULL
for (setting in settings) {
  pp <- panel(focal, setting[[2]], setting[[3]], setting[[4]], setting[[5]])
  result <- did(pp, setting[[1]], setting[[6]], setting[[7]])
  if (is.null(result)) next
  specs[[length(specs) + 1L]] <- result$row
  if (is.null(primary)) {primary <- pp; S$primary <- as.list(result$row[1])}
}
all_blitz <- panel(focal); fixed180 <- panel(focal, "180")
common <- intersect(all_blitz$player, fixed180$player)
for (item in list(list(all_blitz, "Common players: all blitz"), list(fixed180, "Common players: 3|0 only"))) {
  result <- did(item[[1]][player %in% common], item[[2]])
  if (!is.null(result)) specs[[length(specs) + 1L]] <- result$row
}
specs <- rbindlist(specs); output(specs, "did_specifications")
fwrite(primary, file.path(CLEAN, "primary_player_pool_week.csv"))
specs[, label := factor(specification, levels = rev(specification))]
plot <- ggplot(specs, aes(estimate, label)) + geom_errorbar(aes(xmin = ci_low, xmax = ci_high), orientation = "y", width = .2, color = COLORS[["bullet"]]) +
  geom_point(color = COLORS[["bullet"]]) + geom_vline(xintercept = 150, linetype = 2) + geom_vline(xintercept = 0, color = "grey70") +
  labs(title = "Estimated bullet shift depends on control and panel construction", x = "Difference-in-differences estimate (rating points)", y = NULL)
save_figure(plot, "04_did_sensitivity", 11, 5.5); specs[, label := NULL]
event <- eventstudy(primary); events <- event$events; output(events, "event_study"); S$pretrend_p <- event$pretrend_p
plot <- ggplot(events, aes(event_week, estimate)) + geom_line(color = COLORS[["bullet"]]) +
  geom_errorbar(aes(ymin = ci_low, ymax = ci_high), width = .2, color = COLORS[["bullet"]]) + geom_point(color = COLORS[["bullet"]]) +
  geom_vline(xintercept = 0, linetype = 2) + geom_hline(yintercept = 0, color = "grey60") + geom_hline(yintercept = 150, linetype = 3) +
  labs(title = "Bullet versus blitz: event-study contrasts", x = "Event week; reference = -1; week 0 omitted", y = "Relative rating difference (points)")
save_figure(plot, "05_event_study", 9, 4.6)

collapse <- primary[, .(rating = mean(rating)), by = .(player, pool, post)]
wide <- dcast(collapse, player ~ pool + post, value.var = "rating")
changes <- wide[, .(player, bullet_change = bullet_1 - bullet_0, blitz_change = control_1 - control_0)]
changes[, did := bullet_change - blitz_change]; output(changes, "player_level_changes")
RNGkind("Mersenne-Twister", "Inversion", "Rejection"); set.seed(20201011)
boot <- bootstrap_mean(changes$did)
S$paired_bootstrap <- list(n_players = nrow(changes), estimate = mean(changes$did), ci_low = unname(quantile(boot, .025)), ci_high = unname(quantile(boot, .975)))
p1 <- ggplot(changes, aes(blitz_change, bullet_change)) + geom_point(color = COLORS[["bullet"]], alpha = .8) +
  geom_abline(slope = 1, intercept = 0, linetype = 3) + labs(title = "Paired changes across policy periods", x = "Within-player blitz change (points)", y = "Within-player bullet change (points)")
p2 <- ggplot(changes, aes(did)) + geom_histogram(bins = 12, fill = COLORS[["bullet"]], color = "white") +
  geom_vline(xintercept = 150, linetype = 2) + labs(title = "Heterogeneity across matched players", x = "Player-specific bullet minus blitz change", y = "Number of players")
save_multi(list(p1, p2), "06_player_changes")
composition <- rbindlist(lapply(c("bullet", "blitz", "rapid"), function(pool) {
  a <- focal[time_class == pool]; matched <- dcast(a[, .(rating = mean(rating)), by = .(player, post)], player ~ post, value.var = "rating")
  matched <- matched[!is.na(`0`) & !is.na(`1`)]
  data.table(pool = pool, pooled_game_weighted_change = mean(a[post == 1, rating]) - mean(a[post == 0, rating]),
    balanced_equal_player_change = mean(matched$`1` - matched$`0`), balanced_players = nrow(matched),
    pre_players = uniqueN(a[post == 0, player]), post_players = uniqueN(a[post == 1, player]))
}))
output(composition, "composition_contrasts"); S$composition <- records(composition)
long <- melt(composition, id.vars = "pool", measure.vars = c("pooled_game_weighted_change", "balanced_equal_player_change"), variable.name = "weighting")
long[, weighting := factor(weighting, labels = c("All observations: game weighted", "Both periods: equal player weight"))]
plot <- ggplot(long, aes(pool, value, fill = weighting)) + geom_col(position = "dodge") +
  scale_fill_manual(values = c(COLORS[["blitz"]], COLORS[["bullet"]])) + geom_hline(yintercept = 0, color = "grey60") +
  labs(title = "Changing participation alters the apparent rating shift", x = "Rating pool", y = "Post minus pre rating (points)", fill = NULL)
save_figure(plot, "07_composition", 8, 4.5)
tc <- dcast(focal[, .N, by = .(time_control, post)], time_control ~ post, value.var = "N", fill = 0)
setnames(tc, c("0", "1"), c("pre", "post")); output(tc, "time_control_counts")
classes <- games[time_control == "600", .(n = .N), by = .(time_class, post)]; setorder(classes, time_class, post)
S$ten_minute <- list(unique_games = nrow(games[time_control == "600"]), class_counts = records(classes))
trans <- focal[time_class == "bullet" & post == 1 & !is.na(prev_rating) & prev_end < POLICY]
trans[, days_after := (end_time - POLICY) / 86400]
output(trans[, .(player, date, rating_change, score, days_after, gap_hours)], "policy_crossing_transitions")
S$transitions <- list(n = nrow(trans), median_change = median(trans$rating_change), mean_change = mean(trans$rating_change), median_days_after = median(trans$days_after))
p1 <- ggplot(trans, aes(days_after, rating_change, color = score)) + geom_point() + scale_color_viridis_c(limits = c(0, 1), name = "Current score") +
  geom_hline(yintercept = 150, linetype = 2) + labs(title = "First observed bullet game after 10 September", x = "Days after announcement", y = "Change since prior bullet game (points)")
p2 <- ggplot(trans, aes(rating_change)) + geom_histogram(bins = 12, fill = COLORS[["bullet"]], color = "white") +
  geom_vline(xintercept = 150, linetype = 2) + labs(title = "Policy-crossing changes include game updates", x = "Observed rating change (points)", y = "Number of players")
save_multi(list(p1, p2), "08_rollout", 11, 4.5)

decisive <- copy(games[white_score != .5]); decisive[, `:=`(white_win = as.integer(white_score), gap100 = rating_gap / 100)]
outcome <- glm(white_win ~ gap100 + factor(time_class) + post + gap100:post, data = decisive,
  family = binomial(), control = glm.control(epsilon = 1e-12, maxit = 100))
oc <- coefficient_table(outcome, decisive$pair); output(oc, "retrospective_outcome_logit")
S$outcome <- list(n = nrow(decisive), pairs = uniqueN(decisive$pair), gap100 = unname(coef(outcome)["gap100"]),
  post_interaction = unname(coef(outcome)["gap100:post"]), post_interaction_p = oc[term == "gap100:post", pvalue])
decisive[, bin := cut(rating_gap, breaks = seq(-650, 650, 100))]
cal <- decisive[!is.na(bin), .(gap = mean(rating_gap), win = mean(white_win), n = .N), by = bin][n >= 20]
setorder(cal, bin); cal[, bin := NULL]; output(cal, "postgame_gap_outcome")
reference <- data.table(gap = seq(-600, 600), win = probability(seq(-600, 600)))
plot <- ggplot(cal, aes(gap, win)) + geom_line(color = COLORS[["blitz"]]) + geom_point(color = COLORS[["blitz"]]) +
  geom_line(data = reference, linetype = 2, color = "grey50") +
  labs(title = "Post-game ratings are associated with outcomes", x = "Published White minus Black post-game rating", y = "White win fraction among decisive games")
save_figure(plot, "09_retrospective_association", 8, 4.5)

rematches <- copy(games); setorder(rematches, pair, time_class, end_time, game_id)
columns <- c("white", "black", "white_rating", "black_rating", "end_time")
rematches[, paste0("prior_", columns) := shift(.SD), by = .(pair, time_class), .SDcols = columns]
rematches[, `:=`(prior_wr = fifelse(white == prior_white, prior_white_rating, prior_black_rating),
  prior_br = fifelse(black == prior_black, prior_black_rating, prior_white_rating),
  start_stamp = as.numeric(as.POSIXct(substr(start_time, 1, 19), format = "%Y-%m-%dT%H:%M:%S", tz = "UTC")))]
rematches[, rematch_gap_seconds := start_stamp - prior_end_time]
observed <- rbindlist(list(games[, .(game_id, time_class, end_time, player = white)], games[, .(game_id, time_class, end_time, player = black)]))
setorder(observed, player, time_class, end_time, game_id)
observed[, prior_observed_end := shift(end_time), by = .(player, time_class)]
rematches[observed, prior_observed_white := i.prior_observed_end, on = .(game_id, white = player)]
rematches[observed, prior_observed_black := i.prior_observed_end, on = .(game_id, black = player)]
rm <- rematches[!is.na(prior_end_time) & prior_observed_white == prior_end_time & prior_observed_black == prior_end_time &
  rematch_gap_seconds >= 0 & rematch_gap_seconds <= 300 & white_score != .5]
rm[, `:=`(lag_gap = prior_wr - prior_br, y = as.integer(white_score))]
rm[, delta_gap := rating_gap - lag_gap]
write_csv_gz(rm, file.path(CLEAN, "adjacent_rematches.csv.gz"))
predictions <- list(postgame = probability(rm$rating_gap), lagged_rematch = probability(rm$lag_gap))
losses <- lapply(predictions, function(p) -(rm$y * log(pmax(1e-9, pmin(1 - 1e-9, p))) + (1 - rm$y) * log(pmax(1e-9, pmin(1 - 1e-9, 1 - p)))))
metrics <- rbindlist(lapply(names(predictions), function(name) {
  p <- predictions[[name]]
  data.table(rating_source = name, n = nrow(rm), accuracy = mean((p >= .5) == rm$y), brier = mean((p - rm$y)^2), log_loss = mean(losses[[name]]))
}))
output(metrics, "rematch_leakage_metrics"); S$leakage_metrics <- records(metrics)
rm[, loss_difference := losses$lagged_rematch - losses$postgame]
pairloss <- rm[, .(loss_difference = mean(loss_difference)), by = pair]; setorder(pairloss, pair)
bs <- bootstrap_mean(pairloss$loss_difference)
S$leakage_paired <- list(pairs = nrow(pairloss), equal_pair_logloss_gain = mean(pairloss$loss_difference),
  ci_low = unname(quantile(bs, .025)), ci_high = unname(quantile(bs, .975)),
  median_update_white_win = median(rm[y == 1, delta_gap]), median_update_black_win = median(rm[y == 0, delta_gap]))
p1 <- ggplot(rm, aes(factor(y, labels = c("Black wins", "White wins")), delta_gap)) + geom_boxplot(outlier.shape = NA) +
  coord_cartesian(ylim = quantile(rm$delta_gap, c(.01, .99))) + geom_hline(yintercept = 0, color = "grey60") +
  labs(title = "The final rating gap contains the outcome", x = "Result of current rematch", y = "Post-game minus prior rating gap (points)")
p2 <- ggplot(metrics, aes(factor(rating_source, levels = c("postgame", "lagged_rematch"), labels = c("Post-game\ninformation", "Prior rematch\ninformation")), log_loss, fill = rating_source)) +
  geom_col() + scale_fill_manual(values = c(postgame = COLORS[["bullet"]], lagged_rematch = COLORS[["blitz"]])) + guides(fill = "none") +
  labs(title = "Same games, fixed probability curve", x = "Rating measurement used", y = "Mean log loss (lower is better)")
save_multi(list(p1, p2), "10_leakage_audit", 11, 4.5)
rates <- games[, .(n = .N, draw_rate = mean(white_score == .5), white_score = mean(white_score), moves_median = median(moves_proxy, na.rm = TRUE)), by = time_class]
setorder(rates, time_class); output(rates, "unique_game_descriptive"); S$unique_game_descriptive <- records(rates)
p1 <- ggplot(rates, aes(time_class, draw_rate * 100, fill = time_class)) + geom_col() + scale_fill_manual(values = COLORS) + guides(fill = "none") +
  labs(title = "Draw frequency varies across time controls", x = "Rating pool", y = "Draws as share of unique games (%)")
p2 <- ggplot(games, aes(time_class, moves_proxy)) + geom_boxplot(outlier.shape = NA) + coord_cartesian(ylim = c(0, 100)) +
  labs(title = "Game length from PGN move counters", x = "Rating pool", y = "Last full-move number (proxy)")
save_multi(list(p1, p2), "11_game_characteristics", 11, 4.5)
illustration <- data.table(rating = rep(seq(1200, 2800, 400), 2), displayed = c(seq(1200, 2800, 400), seq(1200, 2800, 400) + 150),
  curve = rep(c("Original ratings", "Uniform +150 rebase"), each = 5))
p1 <- ggplot(illustration, aes(rating, displayed, color = curve)) + geom_line() + geom_point() +
  scale_color_manual(values = c(COLORS[["blitz"]], COLORS[["bullet"]])) + labs(title = "A common offset changes levels", x = "Original rating (illustrative)", y = "Displayed rating (illustrative)", color = NULL)
illustration <- data.table(gap = rep(seq(-600, 600, length.out = 100), 2), curve = rep(c("Before rebase", "Both players +150"), each = 100))
illustration[, p := probability(gap)]
p2 <- ggplot(illustration, aes(gap, p, color = curve, linetype = curve)) + geom_line(linewidth = .8) +
  scale_color_manual(values = c(COLORS[["blitz"]], COLORS[["bullet"]])) +
  labs(title = "A common offset preserves rating differences", x = "Player A minus player B rating", y = "Elo-shaped expected score", color = NULL, linetype = NULL)
save_multi(list(p1, p2), "12_rebase_invariance", 11, 4.5)
placebos <- list()
for (cutoff in c(-10L, -8L, -6L, -4L)) {
  pp <- copy(primary[event_week < 0]); pp[, post := as.integer(event_week >= cutoff)]; pp[, treat := bullet * post]
  result <- did(pp, paste0("Pre-period placebo: week ", cutoff))
  if (!is.null(result)) {row <- result$row; row[, cutoff := cutoff]; placebos[[length(placebos) + 1L]] <- row}
}
placebos <- rbindlist(placebos); output(placebos, "placebo_dates"); S$placebos <- records(placebos)
nodes <- data.table(id = c("policy", "offset", "rating", "skill", "selection", "result"),
  x = c(1.4, 5, 8.6, 1.4, 5, 8.6), y = c(3.1, 3.1, 2, 1, 1, .45),
  label = c("Rating-policy\nannouncement", "Mechanical\nrating offset", "Published\npost-game rating", "Underlying skill\nand other shocks", "Participation /\nopponent mix", "Game result"))
edges <- data.table(from = c("policy", "offset", "policy", "skill", "skill", "selection", "selection", "result"),
  to = c("offset", "rating", "selection", "selection", "result", "rating", "result", "rating"))
edges <- merge(edges, nodes[, .(from = id, x, y)], by = "from")
edges <- merge(edges, nodes[, .(to = id, xend = x, yend = y)], by = "to")
plot <- ggplot() + geom_curve(data = edges, aes(x, y, xend = xend, yend = yend), curvature = .08,
  arrow = grid::arrow(length = grid::unit(.12, "inches")), color = "#677783") +
  geom_label(data = nodes, aes(x, y, label = label), fill = "#f4f6f8", color = "#253442", size = 3.4) +
  coord_cartesian(xlim = c(0, 10), ylim = c(0, 4)) + theme_void() +
  labs(title = "Why a rating jump does not identify a skill improvement")
save_figure(plot, "13_causal_structure", 10, 4.4)
S$specifications <- records(specs)
S$implementation <- list(language = "R", R_version = as.character(getRversion()),
  bootstrap_seed = 20201011L, bootstrap_rng = "Mersenne-Twister / Inversion / Rejection", bootstrap_replications = 10000L,
  cluster_correction = "G/(G-1)*(N-1)/(N-K); Student-t with G-1 degrees of freedom")
write_json(S, file.path(OUT, "summary.json"))
writeLines(capture.output(sessionInfo()), file.path(OUT, "session_info.txt"))
message("Completed R analysis: ", S$audit$unique_games, " unique games; primary DiD = ", round(S$primary$estimate, 6), " points.")
