# Earlier work and research-question selection

Search date: 11 October 2026. I conducted a targeted public-web search; it is not a systematic scholarly review or a guarantee of global novelty.

## Direct earlier work found

1. [Tushar Sharma, Predicting Rapid Ratings on Chess.com (2023)](https://www.chess.com/blog/tusharsharma96/predicting-rapid-ratings-on-chess-com-a-data-driven-approach): a cross-sectional regression of rapid ratings on other rating categories. This rules out presenting generic cross-rating regression as a new question.
2. [ChessIQ, keyurc2332](https://github.com/keyurc2332/ChessIQ): a public project explicitly discussing post-game rating leakage. I credit that timing issue to prior work. I use observed preceding rematches rather than assuming symmetric rating exchanges.
3. [David Smerdon, The Fighting Chess Index (2021)](https://www.davidsmerdon.com/?p=2168): an author publication using descriptive metrics, PCA and rating adjustment. It demonstrates that broad chess-statistics projects already exist.
4. [Mark Glickman, The Glicko system](https://www.glicko.net/glicko/glicko.pdf): original rating-system specification.
5. [Bertrand, Duflo and Mullainathan, DiD inference](https://www.nber.org/papers/w8841), [Conley and Taber, few policy changes](https://www.nber.org/papers/t0312), and [Jonathan Roth, pre-tests](https://www.jonathandroth.com/assets/files/roth_pretrends_testing.pdf): established econometric methods informing this application.

The first three entries are author publications or projects with directly viewed primary pages. They are not all peer-reviewed research articles. Repository contents can change after retrieval.

## Main refined question

How much does a measured chess rating-reform effect depend on control-pool definition, participation and weighting when a second reform simultaneously affects the nominal comparison pool?

I found no directly matching combined study in the targeted results I reviewed. My contribution is a reproducible application and sensitivity audit of this frozen dataset, not a claim that no earlier work exists anywhere.

## Query ledger

- Chess.com September 2020 rating analysis regression
- Chess.com 150 bullet difference-in-differences
- chess post-game rating leakage
- chess rating inflation empirical study online
- Chess.com rating causal paper
- chess data leakage ratings prediction
- bullet ratings 2020 study
- chess Glicko calibration study
- Chess.com September 10 control group
- bullet blitz reclassification difference
- chess rating 150 points regression
- chess rating reform composition

Related broad hits included rating trajectories, online behavioral studies and outcome-prediction papers. I cite directly verified primary pages as evidence. I excluded a publisher page that I could not fully retrieve from the evidence supporting my results.

## Policy and data documentation

- [Original September 2020 announcement](https://www.chess.com/news/view/10-minute-chess-now-rapid-rated-bullet-ratings-increased)
- [Chess.com PubAPI documentation](https://www.chess.com/news/view/published-data-api), including post-game rating semantics and serial access
- [Public current-GM frame endpoint](https://api.chess.com/pub/titled/GM)
- Monthly archive pattern: `https://api.chess.com/pub/player/{handle}/games/2020/{month}`
- [Lichess rating implementation context](https://lichess.org/page/rating-systems); no Lichess games were mixed into Chess.com estimates
