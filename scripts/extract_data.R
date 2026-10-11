# Reconstruct the analytical units directly from the frozen public archives.
extract_data <- function() {
  cohort <- read_json(file.path(ROOT, "data", "cohort.json"), TRUE)
  active <- cohort$july_active
  rows <- list(); seen <- new.env(hash = TRUE, parent = emptyenv())
  archive_records <- 0L; rejected <- 0L; errors <- character()
  paths <- sort(list.files(file.path(ROOT, "data", "raw"), pattern = "_2020_.*\\.json\\.gz$", full.names = TRUE))
  for (i in seq_along(paths)) {
    con <- gzfile(paths[i], "rt"); archive <- fromJSON(paste(readLines(con, warn = FALSE), collapse = "\n"), simplifyVector = FALSE); close(con)
    if (!is.null(archive$request_error)) errors <- c(errors, basename(paths[i]))
    for (game in archive$games) {
      archive_records <- archive_records + 1L
      if (!isTRUE(game$rated) || !identical(game$rules, "chess") ||
          !game$time_class %in% c("bullet", "blitz", "rapid")) {rejected <- rejected + 1L; next}
      key <- if (is.null(game$uuid) || !nzchar(game$uuid)) game$url else game$uuid
      if (exists(key, envir = seen, inherits = FALSE)) next
      pgn <- if (is.null(game$pgn)) "" else game$pgn
      header_lines <- regmatches(pgn, gregexpr('(?m)^\\[(\\w+) "(.*)"\\]$', pgn, perl = TRUE))[[1]]
      headers <- setNames(sub('^\\[\\w+ "(.*)"\\]$', '\\1', header_lines, perl = TRUE),
        sub('^\\[(\\w+) .*', '\\1', header_lines, perl = TRUE))
      result <- unname(headers["Result"])
      if (is.na(result) || !result %in% c("1-0", "0-1", "1/2-1/2")) {rejected <- rejected + 1L; next}
      wr <- as.numeric(game$white$rating); br <- as.numeric(game$black$rating); end <- as.numeric(game$end_time)
      day <- if ("UTCDate" %in% names(headers)) headers[["UTCDate"]] else headers[["Date"]]
      clock <- if ("UTCTime" %in% names(headers)) headers[["UTCTime"]] else "00:00:00"
      start <- as.POSIXct(paste(gsub(".", "-", day, fixed = TRUE), clock), tz = "UTC")
      if (length(wr) != 1L || length(br) != 1L || length(end) != 1L || is.na(start) ||
          any(!is.finite(c(wr, br, end))) || wr < 100 || wr > 4000 || br < 100 || br > 4000) {rejected <- rejected + 1L; next}
      move_text <- tail(strsplit(pgn, "\n\n", fixed = TRUE)[[1]], 1)
      move_text <- gsub("\\{[^}]*\\}", "", move_text, perl = TRUE)
      counters <- regmatches(move_text, gregexpr("(?<!\\w)(\\d+)\\.(?:\\.\\.)?", move_text, perl = TRUE))[[1]]
      moves <- if (length(counters)) max(as.integer(sub("\\..*", "", counters))) else NA_real_
      rows[[length(rows) + 1L]] <- list(game_id = key, url = game$url, end_time = end,
        start_time = format(start, "%Y-%m-%dT%H:%M:%S+00:00", tz = "UTC"),
        white = tolower(game$white$username), black = tolower(game$black$username),
        white_rating = wr, black_rating = br, white_score = switch(result, "1-0" = 1, "0-1" = 0, "1/2-1/2" = .5),
        time_class = game$time_class, time_control = as.character(game$time_control),
        white_result = game$white$result, black_result = game$black$result,
        eco = if ("ECO" %in% names(headers)) headers[["ECO"]] else "unknown", moves_proxy = moves,
        pgn_rating_match = isTRUE(headers[["WhiteElo"]] == as.character(wr)) && isTRUE(headers[["BlackElo"]] == as.character(br)))
      assign(key, TRUE, envir = seen)
    }
    if (i %% 100L == 0L) message("Read ", i, "/", length(paths), " frozen archives")
  }
  games <- rbindlist(rows); rm(rows); setorder(games, end_time, game_id)
  games <- games[end_time >= as.numeric(as.POSIXct("2020-06-01", tz = "UTC")) & end_time < as.numeric(as.POSIXct("2020-11-01", tz = "UTC"))]
  games[, `:=`(date = format(as.POSIXct(end_time, origin = "1970-01-01", tz = "UTC"), "%Y-%m-%d %H:%M:%S+00:00", tz = "UTC"),
    event_week = as.integer(floor((end_time - POLICY) / 604800)), post = as.integer(end_time >= POLICY),
    rating_gap = white_rating - black_rating, pair = paste(pmin(white, black), pmax(white, black), sep = "|"))]
  white <- copy(games[white %in% active]); white[, `:=`(player = white, rating = white_rating, opponent = black, score = white_score, is_white = 1L)]
  black <- copy(games[black %in% active]); black[, `:=`(player = black, rating = black_rating, opponent = white, score = 1 - white_score, is_white = 0L)]
  focal <- rbindlist(list(white, black)); setorder(focal, player, time_class, end_time, game_id)
  focal[, `:=`(prev_rating = shift(rating), prev_end = shift(end_time), prev_score = shift(score)), by = .(player, time_class)]
  focal[, `:=`(rating_change = rating - prev_rating, gap_hours = (end_time - prev_end) / 3600)]
  write_csv_gz(games, file.path(CLEAN, "unique_games.csv.gz")); write_csv_gz(focal, file.path(CLEAN, "focal_games.csv.gz"))
  audit <- list(frame_n = cohort$frame_n, screened_n = cohort$screened_n, july_active_n = length(active),
    archive_records = archive_records, rejected_archive_rows = rejected, unique_games = nrow(games),
    focal_observations = nrow(focal), deduplicated_eligible_rows = archive_records - rejected - nrow(games),
    archive_errors = as.list(errors), pgn_rating_match_pct = 100 * mean(games$pgn_rating_match),
    start = min(games$date), end = max(games$date))
  list(games = games, focal = focal, audit = audit)
}
