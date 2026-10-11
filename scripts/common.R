# Shared paths, data I/O, and explicit cluster-robust inference.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)][1])
ROOT <- dirname(dirname(normalizePath(script, winslash = "/", mustWork = TRUE)))
project_library <- file.path(ROOT, ".R-library")
if (dir.exists(project_library)) .libPaths(c(project_library, .libPaths()))
invisible(Sys.setlocale("LC_COLLATE", "C"))
suppressPackageStartupMessages({library(data.table); library(jsonlite); library(ggplot2)})
data.table::setDTthreads(2L)
OUT <- file.path(ROOT, "results")
FIG <- file.path(ROOT, "report", "figures")
CLEAN <- file.path(ROOT, "data", "processed")
POLICY <- as.numeric(as.POSIXct("2020-09-10", tz = "UTC"))
COLORS <- c(bullet = "#b35828", blitz = "#256b91", rapid = "#64835c")
for (directory in c(OUT, FIG, CLEAN)) dir.create(directory, recursive = TRUE, showWarnings = FALSE)
theme_set(theme_minimal(base_size = 12) + theme(panel.grid.minor = element_blank(),
  plot.title = element_text(color = "#253442"), legend.position = "bottom"))
read_json <- function(path, simplify = FALSE) jsonlite::fromJSON(path, simplifyVector = simplify)
write_json <- function(object, path) jsonlite::write_json(object, path, auto_unbox = TRUE,
  pretty = TRUE, digits = NA, null = "null", na = "null")
records <- function(x) lapply(seq_len(nrow(x)), function(i) as.list(x[i]))
output <- function(x, name) fwrite(x, file.path(OUT, paste0(name, ".csv")), na = "")
read_csv_gz <- function(path) {
  con <- gzfile(path, "rt"); on.exit(close(con)); as.data.table(read.csv(con, stringsAsFactors = FALSE, check.names = FALSE))
}
write_csv_gz <- function(x, path) {
  con <- gzfile(path, "wt"); on.exit(close(con)); write.csv(x, con, row.names = FALSE, na = "")
}
save_figure <- function(plot, name, width = 10, height = 4.5) {
  ggsave(file.path(FIG, paste0(name, ".pdf")), plot, width = width, height = height,
    device = grDevices::pdf, family = "Helvetica", useDingbats = FALSE)
  ggsave(file.path(FIG, paste0(name, ".png")), plot, width = width, height = height, dpi = 220)
}
save_multi <- function(plots, name, width = 10, height = 4.5) {
  draw <- function() {
    grid::grid.newpage()
    for (i in seq_along(plots)) print(plots[[i]], newpage = FALSE,
      vp = grid::viewport(x = (i - .5) / length(plots), width = 1 / length(plots), height = 1))
  }
  pdf(file.path(FIG, paste0(name, ".pdf")), width = width, height = height, family = "Helvetica", useDingbats = FALSE)
  draw(); dev.off()
  png(file.path(FIG, paste0(name, ".png")), width = width * 220, height = height * 220, res = 220)
  draw(); dev.off()
}
# CR1 covariance: account/pair score sums, with G/(G-1)*(N-1)/(N-K).
# For WLS, scores use w_i*x_i*e_i and the bread uses X'WX.
# For binomial GLM, scores use x_i*(y_i-mu_i), with the information bread.
cluster_vcov <- function(fit, cluster) {
  X <- model.matrix(fit); N <- nrow(X); K <- ncol(X)
  stopifnot(fit$rank == K, length(cluster) == N)
  if (inherits(fit, "glm")) {
    mu <- fitted(fit); score <- X * as.numeric(fit$y - mu)
    bread <- solve(crossprod(X * sqrt(mu * (1 - mu))))
  } else {
    w <- if (is.null(fit$weights)) rep(1, N) else fit$weights
    score <- X * as.numeric(w * residuals(fit))
    bread <- solve(crossprod(X * sqrt(w)))
  }
  sums <- rowsum(score, as.character(cluster), reorder = TRUE)
  G <- nrow(sums); stopifnot(G >= 3, N > K)
  V <- bread %*% crossprod(sums) %*% bread * G/(G-1) * (N-1)/(N-K)
  dimnames(V) <- list(colnames(X), colnames(X))
  list(vcov = V, df = G - 1, clusters = G)
}
coefficient_table <- function(fit, cluster) {
  robust <- cluster_vcov(fit, cluster); b <- coef(fit); se <- sqrt(diag(robust$vcov))
  critical <- qt(.975, robust$df)
  data.table(term = names(b), coefficient = unname(b), se = unname(se),
    pvalue = 2 * pt(-abs(b / se), robust$df),
    ci_low = unname(b - critical * se), ci_high = unname(b + critical * se))
}
