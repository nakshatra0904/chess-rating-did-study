# Data attribution and scope

Source: Chess.com Public Data API, https://www.chess.com/news/view/published-data-api . I retrieved the JSON monthly archives and PGN records through read-only public endpoints. Source URLs, UTC retrieval times and uncompressed-response SHA-256 hashes are in data/request_log.jsonl.

The data include public handles, public game URLs, public results, ratings, times, and move records. I requested no chats, credentials, emails or private profiles. The GM frame is contemporary at retrieval, not a historical roster of 2020 grandmasters.

Public access does not transfer ownership. The MIT license covers the original code and report, not the source platform data, third-party works, protected artwork, or platform brand. This project does not assert an unrestricted downstream data license.

Frozen archives can differ from later endpoint responses; use frozen data for exact reproduction. The unavailable archive is logged as an error and not imputed.
