# Restore the exact R package versions recorded for this analysis.
args <- commandArgs(FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)][1])
root <- dirname(dirname(normalizePath(script, winslash = "/")))
library_path <- file.path(root, ".R-library")
dir.create(library_path, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(library_path, .libPaths()))
Sys.setenv(RENV_PATHS_CACHE = file.path(root, ".cache", "renv"),
  RENV_PATHS_ROOT = file.path(root, ".cache", "renv-root"))
if (identical(getOption("repos")[["CRAN"]], "@CRAN@")) options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv", lib = library_path)
renv::restore(project = root, library = library_path, lockfile = file.path(root, "renv.lock"), prompt = FALSE)
