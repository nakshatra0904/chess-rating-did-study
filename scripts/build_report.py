"""Generate the full LaTeX report from computed results; no estimates are hand-entered."""
import json,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'outputs'/'chess-rating-study'
if (ROOT/'data'/'raw').exists():P=ROOT
S=json.loads((P/'results'/'summary.json').read_text())
A=S['audit'];D=S['primary'];B=S['paired_bootstrap'];L=S['leakage_paired'];T=S['transitions']
V={x['specification']:x for x in S['specifications']}
def n(x):return f'{int(x):,}'
def f(x,d=1):return f'{float(x):,.{d}f}'
def pct(x):return f'{float(x)*100:.1f}\\%'
def esc(s):
    return str(s).replace('&',r'\&').replace('_',r'\_').replace('%',r'\%').replace('#',r'\#')
parts=[r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=24mm,headheight=15pt]{geometry}
\usepackage[T1]{fontenc}
\usepackage{mathpazo,helvet,courier}
\usepackage{graphicx,booktabs,longtable,array,amsmath,amssymb,xcolor,float,fancyhdr,titlesec,hyperref}
\definecolor{ink}{HTML}{243746}
\definecolor{accent}{HTML}{256B91}
\definecolor{rust}{HTML}{B35828}
\hypersetup{colorlinks=true,linkcolor=accent,urlcolor=accent,citecolor=accent,pdftitle={Rating shifts without identified skill shifts},pdfauthor={nakshatra0904}}
\titleformat{\section}{\Large\sffamily\bfseries\color{ink}}{\thesection}{.6em}{}
\titleformat{\subsection}{\large\sffamily\bfseries\color{ink}}{\thesubsection}{.6em}{}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small\sffamily Chess rating policy and measurement}\fancyhead[R]{\small\sffamily Empirical report}\fancyfoot[C]{\thepage}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\renewcommand{\arraystretch}{1.15}
\setlength{\emergencystretch}{3em}
\newcommand{\note}[1]{{\small\color{ink} #1}}
\begin{document}
\hypersetup{pageanchor=false}
\begin{titlepage}
\vspace*{1.1cm}
{\sffamily\color{accent}\large ONLINE CHESS / APPLIED ECONOMETRICS\par}
\vspace{1cm}
{\sffamily\bfseries\color{ink}\fontsize{30}{36}\selectfont Rating shifts without identified skill shifts\par}
\vspace{.7cm}
{\sffamily\Large A difference-in-differences study of control-group sensitivity, participation, and post-game measurement around Chess.com's September 2020 reform\par}
\vspace{1cm}
{\large Research and analysis by nakshatra0904\par}
{\large Prepared 11 October 2026\par}
\vfill
\rule{\textwidth}{.7pt}
\vspace{.3cm}
\textbf{Main research question}\par
How much does an apparent rating-policy effect depend on the comparison pool, the players included, and the timing of the rating measurement?\par
\vspace{.3cm}
\textbf{Data window}\par
1 June--31 October 2020. Public monthly Chess.com game archives, retrieved for a deterministically selected cohort.\par
\vspace{.3cm}
\textbf{Evidence standard}\par
I estimate a difference-in-differences model, examine an event study and placebo breaks, and audit rating measurement. I distinguish empirical findings from the assumptions required for causal interpretation.\par
\end{titlepage}
\pagenumbering{roman}\hypersetup{pageanchor=true}
\begingroup\small\setlength{\parskip}{0pt}\tableofcontents\endgroup\clearpage\pagenumbering{arabic}
''']
def add(x):parts.append(x+'\n')
def section(x):add(r'\section{'+x+'}')
def sub(x):add(r'\subsection{'+x+'}')
def fig(name,caption,height=None):
    opts=r'width=\textwidth' if height is None else r'width=\textwidth,height='+height+',keepaspectratio'
    add(r'\begin{figure}[H]\centering\includegraphics['+opts+r']{figures/'+name+r'.pdf}\caption{'+caption+r'}\end{figure}')
def table(headers,rows,layout,caption):
    add(r'\begin{table}[H]\centering\small\caption{'+caption+r'}\begin{tabular}{'+layout+r'}\toprule')
    add(' & '.join(headers)+r' \\ \midrule')
    for row in rows:add(' & '.join(map(str,row))+r' \\')
    add(r'\bottomrule\end{tabular}\end{table}')

section('Executive findings')
add(f"I analyze {n(A['unique_games'])} unique rated standard-chess games and {n(A['focal_observations'])} focal player-game observations from {n(A['july_active_n'])} July-active accounts, selected by screening {n(A['screened_n'])} accounts from a {n(A['frame_n'])}-account grandmaster sampling frame. I investigate an administrative rating change and distinguish displayed rating increases from improvement in chess skill.")
add(f"My primary two-way fixed-effects difference-in-differences (DiD) regression estimates a bullet-versus-blitz shift of \\textbf{{{f(D['estimate'])} rating points}}, with an exploratory player-clustered 95\\% interval of [{f(D['ci_low'])}, {f(D['ci_high'])}]. The estimation sample has {n(D['n_players'])} players and {n(D['n_cells'])} observed player-pool-week cells. This conditional contrast is a cohort-specific estimate; the policy was one platform-wide event, so its uncertainty is not fully captured by treating players as independent policy replications.")
add(f"A simpler matched-player calculation gives {f(B['estimate'])} points, with a player-resampling percentile interval of [{f(B['ci_low'])}, {f(B['ci_high'])}]. The difference from the fixed-effects estimate reflects aggregation and weighting. Both estimates should be compared with the announced 150-point administrative offset, not interpreted as a gain of the same amount in latent ability.")
add(f"The joint test of the five nearest pre-event contrasts has p = {f(S['pretrend_p'],3)}. This diagnostic does not establish parallel trends: pre-tests may have limited power, and multiple co-occurring reforms threaten the comparison even when a pre-test does not reject. I therefore estimate several control definitions, common-player comparisons, pre-period placebos, and a differential-trend sensitivity model.")
add(f"The endpoint's ratings are recorded after the game. In {n(S['leakage_metrics'][0]['n'])} observed adjacent decisive rematches, I compare retrospective performance metrics using post-game and prior-rematch ratings. The equal-pair mean improvement in log loss is {f(L['equal_pair_logloss_gain'],4)}, with a pair-resampling interval of [{f(L['ci_low'],4)}, {f(L['ci_high'],4)}]. This is a measurement audit of information timing, not a new discovery that leakage can occur and not a deployable forecasting validation.")
add(r"\textbf{The most useful distinction in this cohort.} "+f"Removing the directly reclassified 10|0 observations changes the main estimate by only {f(abs(V['Exclude 10|0; balanced; >=3 games']['estimate']-D['estimate']),2)} points. On the common {n(V['Common players: all blitz']['n_players'])}-account sample, changing the comparator from all blitz to 3|0 changes it by about {f(abs(V['Common players: all blitz']['estimate']-V['Common players: 3|0 only']['estimate']))} points. In contrast, weighting cells by their number of games raises the estimate from {f(D['estimate'])} to {f(V['All blitz; game-count weighted']['estimate'])} points. Thus weighting and participant support are more consequential than the direct 10|0 exclusion in this GM-oriented cohort; the result does not establish that comparator contamination is unimportant for the whole platform.")
add(r"\textbf{Contribution.} Prior work already analyzes rating prediction and post-game leakage. My narrower contribution is a reproducible sensitivity study connecting an actual reform to comparator contamination, changing participation, and measurement timing. In a targeted search, I found no directly matching study of this exact combined design; that is a limited search finding, not proof of worldwide novelty.")

section('Earlier work and the refined research question')
sub('What has already been done?')
add(r"Rating models and their uncertainty are established subjects. Glickman's original Glicko formulation adds rating uncertainty to skill estimation \cite{glicko}. Current platform documentation distinguishes implementation details and player pools \cite{chessratings,lichessratings}. I use established rating theory and interpret Chess.com points within their own platform and rating pool.")
add(r"Public applied projects also cover several obvious questions. Sharma's 2023 Chess.com analysis regresses rapid ratings on other ratings \cite{sharma}. The ChessIQ repository explicitly identifies outcome leakage from post-game ratings and PGN fields \cite{chessiq}. Smerdon's Fighting Chess Index demonstrates descriptive construction and regression adjustment of chess performance characteristics \cite{smerdon}. These are direct examples of earlier work; the latter two are public project or author publications, not evidence that every nearby question has been peer reviewed.")
table(['Earlier work','Relevant overlap','Distinction in this report'],[
    ['Glickman, Glicko',r'Uncertainty-aware ratings',r'Empirical policy measurement'],
    ['Sharma (2023)',r'Cross-pool regression',r'Historical within-player contrasts'],
    ['ChessIQ project',r'Post-game rating leakage',r'Observed rematch audit near reform'],
    ['Smerdon (2021)',r'Draw statistics and adjustment',r'Policy comparator sensitivity'],
    ['DiD methods literature',r'Trends and dependent errors',r'Applied audit of one platform event']],
    r'p{3cm}p{4.1cm}p{6cm}','Related work and the narrower empirical contribution')
sub('Search scope and what novelty can mean')
add(r"I searched the public web and consulted primary pages on 11 October 2026. Query families included Chess.com / September 2020 / rating / regression; bullet / 150 / difference-in-differences; chess / post-game rating / leakage; chess / rating inflation / empirical study; and Chess.com / September 10 / control group. I found direct prior work on two candidate topics and narrowed my initial generic rating-prediction question. The repository contains the query ledger and verified source links.")
add(r"My search was targeted, not a systematic review of subscription databases, non-English theses, or every GitHub repository. I found no directly matched study in the results I reviewed. The appropriate novelty claim is therefore an original analysis of this frozen dataset and specification set, conditional on a documented search, rather than a claim that nobody has considered comparison-group sensitivity in chess.")
sub('Main question and secondary questions')
add(r"The central question is whether the apparent effect of a common rating rebase remains similar when the comparison pool and participant mix change. The simultaneous reclassification of 10-minute chess makes blitz a potentially affected comparator. Restricting observations to unchanged time controls may reduce direct composition changes, while leaving pool-wide spillovers unresolved.")
add(r"Three secondary questions are answered: (i) how much do game-weighted and equal-player comparisons differ; (ii) are first observed policy-crossing bullet changes compatible with an offset plus ordinary game updates; and (iii) how do result-associated rating updates alter performance metrics when measured ratings are used retrospectively? I defined all specifications before inspecting their estimated policy coefficients. I expanded the cohort from 128 to 256 screened accounts after observing activity counts, to improve coverage, without using estimated effects as a stopping rule.")

section('Policy context and what a rating measures')
add(r"Chess.com's 10 September 2020 announcement describes two changes: 10|0 games moved from blitz to rapid, and active bullet ratings received an administrative increase of 150 points. The bullet adjustment was applied on a subsequent live-chess login, with a short rollout delay. Eligible rapid ratings could also be raised to the player's higher blitz rating \cite{policy}. The announcement date is therefore an intention-to-treat time marker, not an observed account-level treatment timestamp.")
add(r"A rating is an estimated coordinate within a population and implementation. A uniform offset $c$ applied to both players leaves their difference unchanged: $(r_i+c)-(r_j+c)=r_i-r_j$. Any expectation formula depending only on the difference is invariant to this common rebase. An increase in displayed points can thus be mechanically large while implying no change in relative expected score.")
add(r"For illustration, the Elo-shaped curve is $E_i=1/(1+10^{-(r_i-r_j)/400})$. A hypothetical update $r_i'=r_i+K(s_i-E_i)$ would depend on both result and expectation. This is an illustrative formula, not a reconstruction of Chess.com's Glicko updates. Historical rating deviation, update parameters, refunds, and exact login time are absent from the archives used here.")
fig('12_rebase_invariance','Illustrative mechanism, not empirical observations: a uniform 150-point offset changes absolute levels but preserves pairwise differences. The curve is Elo-shaped and is not fitted to the cohort.')
add(r"Two timing details matter. First, the documented monthly-game JSON ratings are post-game measurements. Second, the PGN rating headers in these data match those JSON values. Treating them as pre-game inputs would import information generated by the outcome into an apparent prediction exercise \cite{pubapi}. I use them as measured outcomes in the policy analysis and interpret the logistic regression as retrospective association.")

section('Data collection, provenance and sample construction')
sub('Reproducible sampling')
add(f"The public GM-title endpoint contained {n(A['frame_n'])} account names at retrieval. I ranked each normalized name by the SHA-256 digest of the fixed string \\texttt{{chess-policy-2020-v1|}} followed by that name. The first {n(A['screened_n'])} names formed the screening sample. Accounts with at least one rated standard bullet, blitz, or rapid game in July 2020 formed the historical active cohort ({n(A['july_active_n'])} accounts). I retrieved complete available archives for June, July, August, September, and October 2020 for those accounts.")
add(r"This is deterministic pseudo-random selection from a contemporary title list, followed by historical activity screening. It is not a probability sample of all 2020 Chess.com users. Accounts that no longer appear in the current frame can be missing; players may have earned titles later; and inactive July accounts are deliberately excluded. Public handles identify accounts, not necessarily distinct people. I do not assume that these accounts already held GM titles in 2020.")
sub('Cleaning and observational units')
add(r"I retain rated standard chess in the three live speed classes, interpret White's result as 1, 0.5, or 0, require numeric ratings between 100 and 4000, normalize usernames, and deduplicate by game UUID (falling back to URL). I exclude variant chess, daily chess, unrated games, and unknown final results. I convert game finish timestamps to UTC; the window ends before 1 November 2020.")
add(r"I maintain two distinct observational units. The unique-game file contains each game once, even when both players are sampled. The focal player-game file contains one row for each sampled participant. A game with two cohort accounts contributes two focal rows but only one unique-game row. Descriptive participant ratings use the latter focal unit; win/draw summaries and outcome regressions use unique games. This prevents duplicate games from being treated as independent outcome observations.")
table(['Stage / property','Count'],[
    ['Current GM account frame',n(A['frame_n'])],['Accounts screened',n(A['screened_n'])],['July-active cohort accounts',n(A['july_active_n'])],
    ['Retrieved archive game records',n(A['archive_records'])],['Rejected archive rows',n(A['rejected_archive_rows'])],
    ['Repeated eligible archive appearances removed',n(A['deduplicated_eligible_rows'])],['Unique eligible games',n(A['unique_games'])],
    ['Focal player-game observations',n(A['focal_observations'])],['Primary panel players',n(D['n_players'])],['Primary panel cells',n(D['n_cells'])]],
    'lr','Sample construction and audit counts')
add(f"The observed eligible timestamps run from {esc(A['start'])} to {esc(A['end'])}. PGN and JSON rating values match in {f(A['pgn_rating_match_pct'],2)}\\% of unique games. Request URLs, retrieval times, status codes, content hashes, the frozen sampling frame, and the selected cohort are included. I record unavailable archives as missing and do not impute their games.")
sub('Descriptive statistics')
rows=[]
for x in S['descriptive']:
    rows.append([x['time_class'],n(x['observations']),n(x['players']),f(x['mean_rating']),f(x['median_rating']),f(x['sd_rating']),f(x['p10_rating']),f(x['p90_rating'])])
table(['Pool','Obs.','Accounts','Mean','Median','SD','P10','P90'],rows,'lrrrrrrr','Published post-game ratings among focal observations, June--October 2020')
add(r"These are game-weighted statistics: a frequent player contributes more observations. The distribution describes this selected cohort's activity, not platform-wide percentiles. Standard deviation describes observed dispersion and is not a standard error. Game outcomes, repeated opponents, and account activity induce dependence that is addressed in model uncertainty only to the extent described below.")
fig('02_distributions','Focal post-game rating distributions before and on/after 10 September 2020. Histograms are normalized within pool-period. Source: frozen Chess.com cohort archives, June--October 2020.')

section('Difference-in-differences design and assumptions')
sub('Two-way fixed-effects DiD specification')
add(r"I anchor seven-day event bins at 00:00 UTC on 10 September 2020. Week $k=\lfloor(t-t_0)/7\text{ days}\rfloor$ is based on game completion time. I omit week 0 (10--16 September) from panel estimation because treatment timing is imprecise. My main panel retains player-pool-week cells containing at least three focal games. Each retained account must have observed qualifying bullet and blitz cells in both periods; it need not appear in every week.")
add(r"""I use difference-in-differences: bullet is the treated pool and blitz is the comparison pool for the same accounts. I compare their changes before and after the announcement, excluding the rollout week. My two-way fixed-effects least-squares specification is
\begin{equation}
\bar R_{ict}=\alpha_{ic}+\lambda_t+\beta\,\mathbf{1}(c=\mathrm{bullet})\mathbf{1}(t\geq1)+\varepsilon_{ict}.
\end{equation}
Here $\alpha_{ic}$ is a player-by-pool fixed effect, $\lambda_t$ is an event-week fixed effect, and $\bar R$ is the mean published post-game rating in the cell. Observed cells receive equal weight. I also estimate a sensitivity model weighted by game count; neither weighting guarantees representativeness.""")
add(r"The coefficient compares the change in bullet with the contemporaneous change in blitz after accounting for persistent player-pool levels and common weekly shifts. Its causal interpretation would require parallel untreated trends in bullet versus the chosen control, no relevant spillovers into blitz, no differential measurement changes, and ignorable changes in observation. These requirements are not secured by the public data.")
sub('Uncertainty and diagnostic tests')
add(r"I calculate regression intervals with the statsmodels cluster-robust covariance, clustering by account and using a Student-$t$ reference with the cluster degrees-of-freedom correction \cite{statsmodels}. I additionally bootstrap entire player contrasts 10,000 times using seed 20201011. This retains within-player dependence, but is a different aggregate estimand from the fixed-effects coefficient. Bootstrap intervals use percentiles, not a claim of exact small-sample coverage.")
add(r"Many games do not imply many independent policy changes. Players share opponents, pool dynamics, and a single announcement. Account clustering does not capture every cross-player shock. The econometric literature documents sensitivity to serial correlation and to having few policy changes \cite{bertrand,conley}. Reported intervals are useful cohort-level diagnostics and do not establish the uncertainty of a counterfactual platform-wide reform effect.")
add(r"I estimate an event study interacting bullet status with each observed event week, relative to week -1. I jointly test the five contrasts for weeks -6 through -2 as a near-event pre-trend diagnostic. I use four earlier dates as placebo breaks, restricting their estimation to pre-announcement observations. Non-rejection is not proof of the identifying assumption, and post-selection on a pre-test can distort inference \cite{roth}. All these checks are exploratory, with no multiplicity-adjusted family-wise significance claim.")
sub('Why a sharp regression discontinuity is not used')
add(r"There is no observed assignment score with a treatment threshold. Calendar time is shared by everyone and coincides with other platform changes, so a sharp regression discontinuity in time would require strong assumptions about contemporaneous shocks. I also do not infer treatment receipt from an outcome-derived rating jump: doing so would select treatment on the dependent variable. The date-indexed design is an announcement-based panel contrast.")
fig('13_causal_structure','Conceptual causal structure. Participation and opponent mix can affect measured ratings; game results also enter post-game ratings. The diagram summarizes mechanisms and is not an estimated causal graph.')

section('Descriptive behavior around the announcement')
fig('01_activity','Focal game observations and their pool shares in anchored seven-day event bins. Boundary bins are incomplete calendar exposure; every series describes the sampled archives, not total site activity. Source: Chess.com archives, June--October 2020.')
add(r"The activity plot identifies changes in the observed mix before interpreting mean ratings. A higher mean can arise because stronger or more active accounts play more games, because players move between speed classes, or because the same players receive a rebase. Weekly game counts are descriptive; no exposure-adjusted behavioral treatment effect is estimated from these counts.")
fig('03_rating_trends','Equal-account weekly means: each account with observed games in a pool-week contributes its own mean rating once. The set of accounts can change by week. Source: Chess.com cohort archives, June--October 2020.')
add(r"Equal-player weighting reduces domination by high-volume players but does not hold membership fixed. The fixed-effects panel and paired-player contrasts below address a different question: how observed ratings changed within accounts that appear in both periods and both main pools. A visual discontinuity in an unbalanced mean is therefore supporting description, not the identifying evidence.")

section('DiD estimates, event study and sensitivity')
add(f"My primary DiD estimate is {f(D['estimate'])} points (clustered SE {f(D['se'])}; {n(D['n_players'])} account clusters). The estimate differs from the announced offset by {f(D['estimate']-150)} points. This discrepancy can reflect later ordinary rating updates, incomplete treatment exposure, the behavior of the comparison pool, and the sample weighting. It does not by itself demonstrate that Chess.com implemented the policy incorrectly.")
rows=[]
for x in S['specifications']:rows.append([esc(x['specification']),f(x['estimate']),f(x['ci_low'])+' to '+f(x['ci_high']),n(x['n_players']),n(x['n_cells'])])
table(['Specification','Estimate',r'95\% interval','Players','Cells'],rows,r'p{6.2cm}rrrr','Difference-in-differences estimates, in rating points; account-clustered intervals')
fig('04_did_sensitivity',r'Each marker is a separate player-pool-week fixed-effects estimate with an exploratory 95\% account-clustered interval. Some specifications change the eligible accounts as well as the controls. Source: Chess.com cohort archives, June--October 2020.')
add(r"The unchanged-control comparison restricts blitz to 3|0, while another specification excludes 10|0 only. My planned 5|0 comparison did not retain the minimum three eligible account clusters, so I omit that specification. These are controls defined by recorded game settings, not randomized comparison groups. The common-player pair of specifications holds the account set fixed between all-blitz and 3|0 comparisons, helping separate account selection from the choice of control observations. Weekly activity support may still differ.")
add(r"The unbalanced model admits more player-pool trajectories; the one-game threshold retains noisier cells; the shorter window reduces long-run drift; the game-count weighting changes the target toward frequent play; and the differential linear-trend model allows bullet to drift differently before and after the break. These are substantive sensitivity checks, not independent confirmations. A trend model also imposes a functional form and can extrapolate a noisy pre-trend.")
fig('05_event_study',r'Event-study bullet-versus-blitz contrasts relative to week -1. Week 0 is excluded. Bars are exploratory account-clustered 95\% intervals; the dotted 150-point line is a policy benchmark. Source: the primary cohort panel, June--October 2020.')
add(f"For the near-event pre-period joint test, p = {f(S['pretrend_p'],3)}. The full event-study path, including uncertainty, is more informative than treating that single number as a pass/fail gate. Persistent lead differences, wide intervals, or large placebo estimates weaken the case that an observed post-event change is attributable entirely to the announcement.")
rows=[[str(x['cutoff']),f(x['estimate']),f(x['ci_low'])+' to '+f(x['ci_high']),f(x['pvalue'],3)] for x in S['placebos']]
table(['Placebo event week','Estimate',r'95\% interval','p-value'],rows,'rrrr','Pre-announcement placebo breaks, using the primary accounts and pre-period cells only')
fig('06_player_changes','Each point is a matched account: equal-week post-minus-pre bullet and blitz changes. The right panel shows their differences; the 150-point line is an announced-offset benchmark. Source: the primary panel.')
add(f"The matched-player bootstrap estimate is {f(B['estimate'])} points, with interval [{f(B['ci_low'])}, {f(B['ci_high'])}]. The player distribution makes heterogeneity visible. Accounts with large changes should not be labeled as unusually improved or as suspicious: the measure includes estimation noise, elapsed time, ordinary results, and selection into play.")

section('Participation, reclassification and the comparator problem')
fig('07_composition','Two different descriptive estimands: all-game mean changes versus mean within-account changes among accounts observed in both periods. Their difference combines activity weighting and account composition. Source: Chess.com archives, June--October 2020.')
rows=[[x['pool'],f(x['pooled_game_weighted_change']),f(x['balanced_equal_player_change']),n(x['balanced_players']),n(x['pre_players']),n(x['post_players'])] for x in S['composition']]
table(['Pool','All-game change','Matched change','Matched','Pre','Post'],rows,'lrrrrr','Participation and weighting contrasts; ratings in points, account counts at right')
add(r"This is an estimand comparison rather than an exact causal decomposition. The two changes use different weights and different sets of accounts. It demonstrates how a pooled statistic can tell a different story from equal-player within-account changes, without assigning the entire difference to one mechanism.")
add(f"The unique-game file contains {n(S['ten_minute']['unique_games'])} 10|0 games. That count determines how informative this cohort is about direct reclassification. Grandmaster accounts may choose speed settings very differently from the wider user population. A small number of 10|0 observations would make this dataset weak evidence about platform-wide migration to rapid even though it can still audit comparator sensitivity.")
rows=[[x['time_class'],'post' if x['post'] else 'pre',n(x['n'])] for x in S['ten_minute']['class_counts']]
if rows:table(['Recorded class','Period','10|0 unique games'],rows,'llr','Observed classification of 10-minute games in the frozen archives')
add(r"Removing 10|0 games from the pre-event blitz sample addresses the directly reclassified observations. It does not restore the counterfactual blitz pool: matchmaking opponents, player allocation, and the rating distribution of the remaining pool can respond to the same reform. Restricting to fixed settings is a useful audit and cannot establish a no-spillover control. Rapid is even less suitable as an untreated control because it was directly affected by the announcement.")
add(r"The honest causal conclusion is thus bounded. The panel can measure a bullet-relative rating shift in the observed accounts and assess its sensitivity. It cannot isolate the effect of the bullet offset from all simultaneous general-equilibrium changes in rating pools, nor identify a change in latent chess skill. A common administrative offset provides a strong mechanism for a level shift, but that mechanism is not evidence of an improvement in ability.")

section('First observed policy crossings and rollout timing')
add(f"There are {n(T['n'])} accounts with an observed bullet rating on both sides of the announcement for which the first post-event game crosses the date from the prior observed bullet game. The median observed change is {f(T['median_change'])} points; the mean is {f(T['mean_change'])}. The median first-observation delay is {f(T['median_days_after'])} days.")
fig('08_rollout','First observed post-announcement bullet game minus the previous observed bullet rating. Scatter shading encodes current score (dark = loss, middle = draw, light = win); the offset line is 150. These changes include game updates and elapsed-time effects. Source: frozen cohort archives.')
add(r"The crossing statistic is not a clean measure of the administrative addition. It includes the result of the first post-event game, possibly multiple intervening rating adjustments, and delayed observation. A player can log in before playing, so first post-game observation is not the login time. The distribution is useful for consistency checks, and should not be converted into a staggered-adoption causal design without genuine treatment timestamps.")

section('Post-game information and outcome regressions')
sub('Retrospective association, not an operational forecast')
add(r"I fit a logistic regression to unique decisive games, with White win as the outcome, the post-game White-minus-Black rating gap in hundreds of points, pool indicators, post-period status, and a gap-by-post interaction. Draws are excluded, so the target is winning conditional on a decisive game, not expected score across all games. Standard errors are clustered by unordered opponent pair. Shared accounts across pairs and site-wide shocks remain sources of dependence.")
add(r"""The descriptive model is
\begin{equation}
\operatorname{logit}\Pr(W_g=1)=a+b\,\Delta R_g/100+\eta_c+d\,Post_g+q\,(\Delta R_g/100)Post_g.
\end{equation}
Because $\Delta R_g$ is measured after game $g$, $b$ and $q$ cannot be read as ex ante predictive accuracy or as causal effects of ratings on winning.""")
add(f"I fit the model using {n(S['outcome']['n'])} decisive games from {n(S['outcome']['pairs'])} observed opponent pairs. Its rating-gap coefficient is {f(S['outcome']['gap100'],3)} log-odds per 100 post-game points, while the post-period interaction is {f(S['outcome']['post_interaction'],3)} (p = {f(S['outcome']['post_interaction_p'],3)}). This is a parameter of a retrospective association.")
with (P/'results'/'retrospective_outcome_logit.csv').open(newline='',encoding='utf-8') as src:
    coefficients=list(csv.DictReader(src))
table(['Term','Coefficient','SE',r'95\% interval'],[[esc(x['term']),f(x['coefficient'],3),f(x['se'],3),f(x['ci_low'],3)+' to '+f(x['ci_high'],3)] for x in coefficients],r'p{5.5cm}rrr','Retrospective logistic regression; coefficients in log-odds, pair-clustered intervals')
fig('09_retrospective_association','Binned White win fractions for decisive games against post-game rating differences, with at least 20 games per bin. The Elo-shaped line is an illustrative reference, not an ex ante calibration target for this conditional outcome. Source: unique cohort games.')
sub('An adjacent-rematch timing audit')
add(r"To quantify the timing problem without assuming symmetric rating exchanges, I locate a prior observed game between the same pair in the same speed class. I require the next game's start to be between 0 and 300 seconds after that game's end, and require that prior game to be the latest observed game for both accounts in that class. I then take both players' lagged ratings from the preceding game's post-game values, allowing color to switch.")
add(r"At least one sampled account's complete monthly archive is available, but an unsampled opponent could have an unobserved intervening game elsewhere. Five-minute adjacency is therefore a defensible proxy for prior information, not a guarantee of exact pre-game state. Refunds and other updates may also occur. No opponent rating is reconstructed by forcing a zero-sum points exchange, since uncertainty-aware rating updates need not be symmetric.")
rows=[[esc(x['rating_source']),n(x['n']),pct(x['accuracy']),f(x['brier'],4),f(x['log_loss'],4)] for x in S['leakage_metrics']]
table(['Rating source','Games','Accuracy','Brier','Log loss'],rows,r'p{4.8cm}rrrr','Same decisive rematches, fixed Elo-shaped probability mapping; lower losses are better')
fig('10_leakage_audit','Left: post-game rating gap minus prior-rematch gap, grouped by the current result; boxplots omit outliers for display. Right: mean log loss using the same fixed probability curve on the same games. Source: adjacent decisive rematches, June--October 2020.')
add(f"Median gap updates are {f(L['median_update_white_win'])} points when White wins and {f(L['median_update_black_win'])} when Black wins. The equal-pair mean log-loss gain from post-game information is {f(L['equal_pair_logloss_gain'],4)}, with percentile interval [{f(L['ci_low'],4)}, {f(L['ci_high'],4)}], resampling {n(L['pairs'])} opponent-pair clusters 10,000 times. Game-weighted mean losses in the table and equal-pair differences target different weights.")
add(r"This is a controlled timing comparison, not a learned prediction competition: the probability mapping is fixed and no model is tuned on future games. Its advantage is interpretability; its limitation is that an Elo-shaped curve is not a fitted Glicko forecast and the decisive-game restriction changes the target. The result shows how endpoint timing can alter apparent accuracy in this sample. It does not establish that every Chess.com prediction project is invalid, and it does not reproduce all conclusions of ChessIQ.")

section('Additional descriptive game analysis')
rows=[[x['time_class'],n(x['n']),pct(x['draw_rate']),f(x['white_score'],3),f(x['moves_median'])] for x in S['unique_game_descriptive']]
table(['Pool','Unique games','Draw share','White mean score','Median length'],rows,'lrrrr','Unique-game descriptive statistics; length is the last full-move number in PGN')
fig('11_game_characteristics','Draw shares and distributions of game length by speed class. Length is a PGN move-counter proxy rather than exact ply count; displayed boxplots omit outliers. Source: unique rated standard games, June--October 2020.')
add(r"Draw rates and game length supply useful context for the outcome analysis. They are not adjusted causal effects of longer thinking time: stronger players, different opponents, selected settings, and event formats may all vary across pools. Likewise, White's score in this cohort does not identify the causal advantage of color without evidence about color assignment and opponent selection.")

section('What can and cannot be concluded')
add(r"The strongest supported result is a reproducible measurement of rating behavior in a clearly defined historical cohort, together with explicit sensitivity to sample construction. The nominal 150-point policy is documented independently of the data, and an exactly common offset preserves relative rating gaps by algebra. These are compatible with a change in displayed rating scale without a demonstrated change in underlying ability.")
add(r"A weaker, conditional statement is that the fitted bullet-versus-blitz panel contrast resembles an announcement effect under untreated parallel trends and negligible comparator spillovers. The simultaneous reform, uncertain treatment timing, incomplete activity support, current-title sampling, and shared pool shocks mean those assumptions remain contestable. I therefore interpret my DiD estimate conditionally and do not label it an identified average treatment effect.")
add(r"Important limits are selection and survivorship; account-versus-person ambiguity; limited account clusters in tightly restricted settings; absent historical rating deviation and exact treatment receipt; rating refunds and possible retrospective archive changes; boundary-week exposure differences; outcome-dependent post-game measurement; rematch selection; and unobserved games by opponents outside sampled archives. Large game counts reduce some descriptive noise but do not remove these identification problems.")
sub('A stronger future causal design')
add(r"A credible extension would first obtain exact account-level rebase timestamps and pre-update ratings, ideally from platform logs, plus a cohort frame fixed before the reform. It would record whether each opponent had already been rebased at match start. Relative-exposure contrasts could then examine temporary mismatches during rollout, with pre-specified short windows and explicit tests for selection into login timing.")
add(r"Even that design would require handling interference: one player's rating is influenced by the opponents' states and by pool-wide matching. A randomized staged rollout, if a platform chose to conduct one, would offer stronger assignment evidence. A randomized experiment on rating display could study behavior while keeping the underlying matchmaking rating fixed; this is a proposal, not an experiment performed here.")
sub('Other interesting questions supported by extensions of these data')
add(r"Three specific follow-ups are promising. First, estimate how incomplete opponent histories affect reconstructed pre-game ratings by varying observed rematch gaps and validating against a fully observed two-account subpanel. Second, decompose category migration using a pre-defined cohort of 10|0 specialists, rather than this GM-oriented sample. Third, study whether post-game information creates different apparent prediction gains for low- versus high-uncertainty accounts when historical RD becomes available. These questions add measurement and identification value instead of repeating a generic rating correlation.")

section('Reproducibility and delivery')
add(r"I provide a complete reproducible project containing frozen compressed API responses, processed datasets, request and hash logs, collection and analysis code, all generated figures in PDF and PNG, numerical result tables, this report's LaTeX source, the compiled PDF, dependency pins, verification utilities, and a README. Rebuilding analysis from the frozen data requires no Chess.com credentials and no fresh data download. Re-fetching is optional and can change the contemporary sampling frame.")
add(r"From the repository root, create a Python environment, install \texttt{requirements.txt}, run \texttt{python scripts/analyze.py}, then run \texttt{python scripts/build\_report.py}. Compile from the report folder using \texttt{tectonic report.tex}; an ordinary XeLaTeX installation can also compile the source twice. The delivered report is actually typeset from LaTeX, with vector figure inputs. The self-contained compiler used for delivery was Tectonic 0.17.0; portable Palatino, Helvetica, and Courier TeX fonts avoid dependence on installed desktop fonts.")
add(r"I release my original code and report text under an MIT license. Public platform data are attributed separately and are not relicensed by the code license. The source archives include public game handles and URLs for provenance; no private chats, emails, or authentication tokens were collected. The repository contains the source files, frozen data, estimates, figures and compiled report needed to inspect and reproduce my analysis.")

add(r'\clearpage\appendix')
section('Variable definitions and analytical checks')
table(['Variable','Definition / timing'],[
    [r'\texttt{game\_id}',r'UUID, with public game URL as fallback'],
    [r'\texttt{rating}',r'Focal account rating after the game, from JSON'],
    [r'\texttt{white\_score}',r'White result: 1, 0.5, 0; unique-game unit'],
    [r'\texttt{score}',r'Focal account score, adjusted for color'],
    [r'\texttt{event\_week}',r'Floor of elapsed UTC time / seven days from 10 Sep'],
    [r'\texttt{post}',r'Descriptive indicator for completion on/after 10 Sep'],
    [r'\texttt{treat}',r'Bullet indicator times post, with week 0 omitted'],
    [r'\texttt{unit}',r'Account-by-rating-pool panel identifier'],
    [r'\texttt{rating\_change}',r'Current minus prior observed focal rating in same pool'],
    [r'\texttt{lag\_gap}',r'White minus Black ratings from previous observed rematch'],
    [r'\texttt{pair}',r'Unordered normalized account pair'],
    [r'\texttt{moves\_proxy}',r'Last numeric full-move counter in PGN']],
    r'p{4.4cm}p{9cm}','Core data dictionary; full columns are retained in processed CSV files')
add(r"Verification checks include uniqueness of game identifiers; one or two focal rows per unique sampled game; valid score and class values; temporal ordering for prior-rematch information; non-overlapping prior/current game times for the rematch audit; sufficient policy variation in the panel; full numerical output without invented rows; raw-response hash consistency; expected figure existence; and PDF text and page rendering checks. The verification file reports actual checks rather than substituting test outcomes for identification arguments.")

section('Source notes and references')
add(r"I consulted the web sources on 11 October 2026. Policy and endpoint semantics rely on the platform's own documentation. Prior applied work is identified by direct author pages or repositories. Literature-search limitations are stated in Section 2. The frozen data and request log are the source for all empirical counts and estimates; figures 12 and 13 are explanatory diagrams.")
add(r'''\begin{thebibliography}{99}
\bibitem{policy} Chess.com (2020). \emph{[Updated] 10 Minute Chess Now Rapid Rated, Bullet Ratings Increased}, 10 September. \url{https://www.chess.com/news/view/10-minute-chess-now-rapid-rated-bullet-ratings-increased}.
\bibitem{pubapi} Chess.com. \emph{Published-Data API}, including monthly archives, game result codes, rating timing, and serial access. \url{https://www.chess.com/news/view/published-data-api}.
\bibitem{chessratings} Chess.com Help Center. \emph{How do ratings work on Chess.com?} \url{https://support.chess.com/en/articles/8566476-how-do-ratings-work-on-chess-com}.
\bibitem{lichessratings} Lichess. \emph{Chess rating systems}. \url{https://lichess.org/page/rating-systems}.
\bibitem{glicko} Glickman, M. E. \emph{The Glicko system}. Technical specification. \url{https://www.glicko.net/glicko/glicko.pdf}.
\bibitem{sharma} Sharma, T. (2023). \emph{Predicting Rapid Ratings on Chess.com: A Data-Driven Approach}. Author's Chess.com blog, 22 May. \url{https://www.chess.com/blog/tusharsharma96/predicting-rapid-ratings-on-chess-com-a-data-driven-approach}.
\bibitem{chessiq} keyurc2332. \emph{ChessIQ: Chess outcome prediction, and the three data leaks that made it look possible}. Public repository; consulted version at retrieval, not a peer-reviewed article. \url{https://github.com/keyurc2332/ChessIQ}.
\bibitem{smerdon} Smerdon, D. (2021). \emph{The Fighting Chess Index}, 10 June. Author's methodological article. \url{https://www.davidsmerdon.com/?p=2168}.
\bibitem{bertrand} Bertrand, M., Duflo, E., and Mullainathan, S. (2004). How Much Should We Trust Differences-in-Differences Estimates? \emph{Quarterly Journal of Economics}, 119(1), 249--275. Working-paper record: \url{https://www.nber.org/papers/w8841}.
\bibitem{conley} Conley, T. and Taber, C. (2005). \emph{Inference with Difference in Differences with a Small Number of Policy Changes}. NBER Technical Working Paper 312. \url{https://www.nber.org/papers/t0312}.
\bibitem{roth} Roth, J. (2022). Pretest with Caution: Event-Study Estimates after Testing for Parallel Trends. \emph{American Economic Review: Insights}, 4(3), 305--322. Author manuscript: \url{https://www.jonathandroth.com/assets/files/roth_pretrends_testing.pdf}.
\bibitem{statsmodels} statsmodels. \emph{Linear regression and robust covariance documentation}. \url{https://www.statsmodels.org/stable/_modules/statsmodels/regression/linear_model.html}.
\end{thebibliography}
\end{document}''')
(P/'report'/'report.tex').write_text('\n'.join(parts),encoding='utf-8')
print('Wrote report/report.tex with computed values, 13 figures and source references.')
