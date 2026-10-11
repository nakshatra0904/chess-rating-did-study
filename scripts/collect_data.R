# I collect a deterministic cohort serially, retaining complete public responses.
entry <- sub("^--file=", "", commandArgs(FALSE)[grepl("^--file=", commandArgs(FALSE))][1])
source(file.path(dirname(normalizePath(entry)), "common.R"))
RAW <- file.path(ROOT, "data", "raw"); dir.create(RAW, recursive = TRUE, showWarnings = FALSE)
read_cached <- function(path) {
  con <- gzfile(path, "rt"); on.exit(close(con))
  fromJSON(paste(readLines(con, warn = FALSE), collapse = "\n"), simplifyVector = FALSE)
}
get_archive <- function(url, filename) {
  path <- file.path(RAW, filename)
  if (file.exists(path)) return(read_cached(path))
  for (attempt in seq_len(4L)) {
    result <- tryCatch(curl::curl_fetch_memory(url, handle = curl::new_handle(
      useragent = "ChessRatingStudy/2.0 (public reproducible statistical research; serial requests)",
      timeout = 60, httpheader = c(Accept = "application/json"))), error = function(e) e)
    if (!inherits(result, "error") && result$status_code %in% c(200L, 404L, 410L)) {
      body <- result$content
      if (result$status_code %in% c(404L, 410L)) body <- charToRaw(toJSON(list(games = list(),
        request_error = paste("HTTP Error", result$status_code)), auto_unbox = TRUE))
      con <- gzfile(path, "wb"); writeBin(body, con); close(con)
      item <- list(url = url, file = paste0("data/raw/", filename),
        retrieved_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"), status = result$status_code)
      if (result$status_code == 200L) {
        item$sha256_uncompressed <- digest::digest(body, algo = "sha256", serialize = FALSE)
        item$bytes <- length(body)
      }
      cat(toJSON(item, auto_unbox = TRUE), "\n", file = file.path(ROOT, "data", "request_log.jsonl"), append = TRUE, sep = "")
      Sys.sleep(.15)
      return(fromJSON(rawToChar(body), simplifyVector = FALSE))
    }
    if (attempt == 4L) stop("Unable to retrieve ", url)
    Sys.sleep(3 * 2^(attempt - 1L))
  }
}
arguments <- commandArgs(TRUE); n <- 256L
if ("--n" %in% arguments) n <- as.integer(arguments[match("--n", arguments) + 1L])
stopifnot(is.finite(n), n >= 1L)
frame <- unlist(get_archive("https://api.chess.com/pub/titled/GM", "titled_GM.json.gz")$players, use.names = FALSE)
names <- unique(tolower(frame))
hashes <- vapply(names, function(name) digest::digest(paste0("chess-policy-2020-v1|", name), algo = "sha256", serialize = FALSE), character(1))
selected <- head(names[order(hashes)], n)
active <- character()
for (i in seq_along(selected)) {
  player <- selected[i]
  archive <- get_archive(paste0("https://api.chess.com/pub/player/", player, "/games/2020/07"), paste0(player, "_2020_07.json.gz"))
  if (any(vapply(archive$games, function(g) isTRUE(g$rated) && identical(g$rules, "chess") && g$time_class %in% c("bullet", "blitz", "rapid"), logical(1)))) active <- c(active, player)
  if (i %% 8L == 0L) message("Screened ", i, "/", length(selected), "; active accounts ", length(active))
}
cohort <- list(sampling_frame = "Chess.com current GM endpoint at retrieval; historical survivor sample",
  seed_string = "chess-policy-2020-v1", frame_n = length(frame), screened_n = length(selected),
  screen_month = "2020-07", selected = as.list(selected), months = as.list(paste0("2020-", sprintf("%02d", 6:10))), july_active = as.list(active))
write_json(cohort, file.path(ROOT, "data", "cohort.json"))
for (i in seq_along(active)) {
  for (month in c(6L, 8L, 9L, 10L)) {
    get_archive(paste0("https://api.chess.com/pub/player/", active[i], "/games/2020/", sprintf("%02d", month)),
      paste0(active[i], "_2020_", sprintf("%02d", month), ".json.gz"))
  }
  message("Completed archive collection for account ", i, "/", length(active))
}
message("Collection complete: ", length(selected), " screened accounts; ", length(active), " July-active accounts.")
