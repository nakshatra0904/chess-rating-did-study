"""Meaningful integrity and timing checks for the frozen chess analysis."""
from pathlib import Path
import sys,json,gzip,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'work'/'vendor').exists():sys.path.insert(0,str(ROOT/'work'/'vendor'))
import pandas as pd,numpy as np
import statsmodels.formula.api as smf
P=ROOT/'outputs'/'chess-rating-study'
if (ROOT/'data'/'raw').exists():P=ROOT
checks=[]
def check(name,condition,detail):
    assert bool(condition),name+': '+str(detail)
    checks.append({'check':name,'passed':True,'detail':detail})
def finite(value):
    if isinstance(value,dict):return all(finite(v) for v in value.values())
    if isinstance(value,list):return all(finite(v) for v in value)
    if isinstance(value,float):return math.isfinite(value)
    return True
summary=json.loads((P/'results'/'summary.json').read_text())
check('All reported numeric results finite',finite(summary),'No NaN or infinity in summary.json')
g=pd.read_csv(P/'data'/'processed'/'unique_games.csv.gz')
f=pd.read_csv(P/'data'/'processed'/'focal_games.csv.gz')
q=pd.read_csv(P/'data'/'processed'/'primary_player_pool_week.csv')
rm=pd.read_csv(P/'data'/'processed'/'adjacent_rematches.csv.gz')
check('Unique game IDs',g.game_id.is_unique,len(g))
check('Valid results',set(g.white_score)<=set([0,.5,1]),sorted(g.white_score.unique().tolist()))
check('Valid speed pools',set(g.time_class)<=set(['bullet','blitz','rapid']),sorted(g.time_class.unique().tolist()))
check('Focal game references valid',f.game_id.isin(g.game_id).all(),len(f))
check('One or two focal records per game',f.groupby('game_id').size().between(1,2).all(),'Unique per sampled participant')
check('Focal account-game IDs unique',not f.duplicated(['game_id','player']).any(),'No participant duplication')
check('PGN and JSON ratings agree',g.pgn_rating_match.all(),'Matches documented post-game values')
check('Primary panel supports treatment contrast',q.event_week.ne(0).all() and q.player.nunique()>=3 and q.n_games.ge(3).all(),{'players':int(q.player.nunique()),'cells':len(q)})
balance=q.groupby(['player','pool','post']).size().unstack(['pool','post']).fillna(0)
check('Primary participants observed in both pools and periods',(balance>0).all().all(),len(balance))
exog=smf.ols('rating ~ C(unit) + C(event_week) + treat',data=q).exog
check('Primary fixed-effects design full rank',np.linalg.matrix_rank(exog)==exog.shape[1],{'columns':int(exog.shape[1]),'rank':int(np.linalg.matrix_rank(exog))})
check('Nonempty adjacent rematch audit',len(rm)>100,{'games':len(rm),'pairs':int(rm.pair.nunique())})
check('Prior-game information predates game start',(rm.start_stamp>=rm.prior_end_time).all() and rm.rematch_gap_seconds.between(0,300).all(),'Maximum start gap 300 seconds')
check('Prior rematch is latest observed for both',(rm.prior_observed_white==rm.prior_end_time).all() and (rm.prior_observed_black==rm.prior_end_time).all(),'Checks observed histories, not unseen opponent games')
hashed=0;unavailable=0
for line in (P/'data'/'request_log.jsonl').read_text().splitlines():
    item=json.loads(line)
    if item.get('status') in (404,410):unavailable+=1;continue
    b=gzip.decompress((P/item['file']).read_bytes())
    assert hashlib.sha256(b).hexdigest()==item['sha256_uncompressed'],item['file']
    hashed+=1
check('Frozen successful-response hashes match',hashed>0,{'checked':hashed,'unavailable_archives':unavailable})
figs=list((P/'report'/'figures').glob('*.pdf'))
check('All publication figures exist',len(figs)==13,'13 vector PDF and 13 matching PNG files')
check('All raster previews exist',all(x.with_suffix('.png').exists() for x in figs),len(figs))
check('Summary counts match processed data',len(g)==summary['audit']['unique_games'] and len(f)==summary['audit']['focal_observations'],{'unique_games':len(g),'focal_rows':len(f)})
result={'checks':checks,'all_passed':True,'scope':'Integrity, observed-history timing, design rank; does not establish causal identification.'}
(P/'results'/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
