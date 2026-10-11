"""Rebuild all analytical data, estimates and publication figures from frozen archives."""
import sys, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'work'/'vendor').exists(): sys.path.insert(0,str(ROOT/'work'/'vendor'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache'/'matplotlib'))
import gzip,json,re,hashlib,math
import numpy as np,pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

P=ROOT/'outputs'/'chess-rating-study'
if (ROOT/'data'/'raw').exists(): P=ROOT # exported repository layout
OUT=P/'results'; FIG=P/'report'/'figures'; CLEAN=P/'data'/'processed'
for d in (OUT,FIG,CLEAN): d.mkdir(parents=True,exist_ok=True)
POLICY=pd.Timestamp('2020-09-10',tz='UTC')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':14,
    'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':220,
    'axes.labelcolor':'#253442','text.color':'#253442','axes.edgecolor':'#aab6c0',
    'grid.color':'#e3e8ec','axes.grid':True,'grid.alpha':0.7,'axes.axisbelow':True})
COLORS={'bullet':'#b35828','blitz':'#256b91','rapid':'#64835c'}
def save(name):
    plt.tight_layout(); plt.savefig(FIG/(name+'.pdf'),bbox_inches='tight');plt.savefig(FIG/(name+'.png'),bbox_inches='tight');plt.close()
def output(df,name): df.to_csv(OUT/(name+'.csv'),index=False)
def extract():
    cohort=json.loads((P/'data'/'cohort.json').read_text()); active=set(cohort['july_active'])
    games={}; records=0; rejected=0; errors=[]
    for f in sorted((P/'data'/'raw').glob('*_2020_*.json.gz')):
        archive=json.loads(gzip.decompress(f.read_bytes()))
        if 'request_error' in archive: errors.append(f.name)
        for g in archive.get('games',[]):
            records+=1
            if not(g.get('rated') and g.get('rules')=='chess' and g.get('time_class') in ('bullet','blitz','rapid')): rejected+=1;continue
            key=g.get('uuid') or g.get('url')
            if key in games:continue
            h=dict(re.findall(r'^\[(\w+) "(.*)"\]$',g.get('pgn',''),re.M))
            result=h.get('Result')
            if result not in ('1-0','0-1','1/2-1/2'):rejected+=1;continue
            try:
                wr=float(g['white']['rating']);br=float(g['black']['rating'])
                end=int(g['end_time']);start=pd.Timestamp(h.get('UTCDate',h.get('Date')).replace('.','-')+' '+h.get('UTCTime','00:00:00'),tz='UTC')
            except (ValueError,TypeError,KeyError):rejected+=1;continue
            if not(100<=wr<=4000 and 100<=br<=4000):rejected+=1;continue
            moves=re.sub(r'\{[^}]*\}','',g.get('pgn','').split('\n\n')[-1])
            # Last numeric move counter is a descriptive move-length proxy.
            nums=re.findall(r'(?<!\w)(\d+)\.(?:\.\.)?',moves)
            games[key]={'game_id':key,'url':g['url'],'end_time':end,'start_time':start.isoformat(),
                'white':g['white']['username'].lower(),'black':g['black']['username'].lower(),
                'white_rating':wr,'black_rating':br,'white_score':{'1-0':1,'0-1':0,'1/2-1/2':.5}[result],
                'time_class':g['time_class'],'time_control':str(g.get('time_control','')),
                'white_result':g['white']['result'],'black_result':g['black']['result'],
                'eco':h.get('ECO','unknown'),'moves_proxy':max(map(int,nums)) if nums else np.nan,
                'pgn_rating_match':h.get('WhiteElo')==str(int(wr)) and h.get('BlackElo')==str(int(br))}
    df=pd.DataFrame(games.values()).sort_values(['end_time','game_id']).reset_index(drop=True)
    df['date']=pd.to_datetime(df.end_time,unit='s',utc=True)
    df=df[(df.date>='2020-06-01')&(df.date<'2020-11-01')].copy()
    df['event_week']=np.floor((df.date-POLICY).dt.total_seconds()/604800).astype(int)
    df['post']=(df.date>=POLICY).astype(int);df['rating_gap']=df.white_rating-df.black_rating
    df['pair']=df[['white','black']].apply(lambda x:'|'.join(sorted(x)),axis=1)
    focal=[]
    for color in ('white','black'):
        a=df[df[color].isin(active)].copy()
        a['player']=a[color]; a['rating']=a[color+'_rating'];a['opponent']=a['black' if color=='white' else 'white']
        a['score']=a.white_score if color=='white' else 1-a.white_score
        a['is_white']=int(color=='white');focal.append(a)
    focal=pd.concat(focal).sort_values(['player','time_class','end_time','game_id'])
    grouped=focal.groupby(['player','time_class'])
    focal['prev_rating']=grouped.rating.shift();focal['prev_end']=grouped.end_time.shift()
    focal['rating_change']=focal.rating-focal.prev_rating
    focal['gap_hours']=(focal.end_time-focal.prev_end)/3600
    focal['prev_score']=grouped.score.shift()
    focal.to_csv(CLEAN/'focal_games.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    df.to_csv(CLEAN/'unique_games.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    audit={'frame_n':cohort['frame_n'],'screened_n':cohort['screened_n'],'july_active_n':len(active),
           'archive_records':records,'rejected_archive_rows':rejected,'unique_games':len(df),'focal_observations':len(focal),
           'deduplicated_eligible_rows':records-rejected-len(df),'archive_errors':errors,
           'pgn_rating_match_pct':100*df.pgn_rating_match.mean(),'start':str(df.date.min()),'end':str(df.date.max())}
    return df,focal,audit

def panel(focal,control='all',minimum=3,balanced=True,window=None):
    b=focal[focal.time_class=='bullet'].copy();b['pool']='bullet'
    c=focal[focal.time_class=='blitz'].copy()
    if control=='no600':c=c[c.time_control!='600']
    if control=='180':c=c[c.time_control=='180']
    if control=='300':c=c[c.time_control=='300']
    c['pool']='control';a=pd.concat([b,c])
    a=a[a.event_week!=0].copy()
    if window is not None:a=a[a.event_week.between(-window,window)]
    pp=a.groupby(['player','pool','event_week'],as_index=False).agg(rating=('rating','mean'),n_games=('rating','size'),score=('score','mean'))
    pp=pp[pp.n_games>=minimum].copy(); pp['post']=(pp.event_week>=1).astype(int);pp['bullet']=(pp.pool=='bullet').astype(int)
    if balanced:
        tab=pp.groupby(['player','pool','post']).size().unstack(['pool','post']).fillna(0)
        if len(tab.columns)<4:return pp.iloc[:0]
        good=tab.index[(tab>0).all(axis=1)];pp=pp[pp.player.isin(good)]
    pp['unit']=pp.player+'|'+pp.pool;pp['treat']=pp.bullet*pp.post
    return pp
def did(pp,name,trend=False,weights=False):
    if pp.player.nunique()<3 or pp.empty:return None,None
    formula='rating ~ C(unit) + C(event_week) + treat'
    if trend:formula+=' + bullet:event_week'
    model=smf.wls(formula,data=pp,weights=pp.n_games if weights else np.ones(len(pp)))
    fit=model.fit(cov_type='cluster',cov_kwds={'groups':pp.player},use_t=True)
    ci=fit.conf_int().loc['treat']
    row={'specification':name,'estimate':fit.params['treat'],'se':fit.bse['treat'],'ci_low':ci.iloc[0],'ci_high':ci.iloc[1],
         'pvalue':fit.pvalues['treat'],'n_cells':len(pp),'n_players':pp.player.nunique(),'r_squared':fit.rsquared}
    return row,fit
def eventstudy(pp):
    a=pp.copy();weeks=sorted(a.event_week.unique());reference=-1
    terms=[]
    for k in weeks:
        if k==reference:continue
        name='event_m'+str(-k) if k<0 else 'event_p'+str(k)
        a[name]=((a.event_week==k)&(a.bullet==1)).astype(int);terms.append((k,name))
    fit=smf.ols('rating ~ C(unit) + C(event_week) + '+' + '.join(n for k,n in terms),data=a).fit(cov_type='cluster',cov_kwds={'groups':a.player},use_t=True)
    rows=[]
    for k,n in terms:
        ci=fit.conf_int().loc[n];rows.append({'event_week':k,'estimate':fit.params[n],'se':fit.bse[n],'ci_low':ci.iloc[0],'ci_high':ci.iloc[1]})
    rows.append({'event_week':-1,'estimate':0,'se':0,'ci_low':0,'ci_high':0})
    pre=[n for k,n in terms if -6<=k<-1]
    R=np.zeros((len(pre),len(fit.params)))
    for j,n in enumerate(pre):R[j,list(fit.params.index).index(n)]=1
    test=fit.wald_test(R,scalar=True)
    return pd.DataFrame(rows).sort_values('event_week'),float(test.pvalue)

def main():
    df,f,audit=extract(); summary={ 'audit':audit }
    desc=f.groupby('time_class').agg(observations=('rating','size'),players=('player','nunique'),mean_rating=('rating','mean'),median_rating=('rating','median'),sd_rating=('rating','std'),p10_rating=('rating',lambda s:s.quantile(.1)),p90_rating=('rating',lambda s:s.quantile(.9)),mean_score=('score','mean')).reset_index()
    output(desc,'descriptive_by_pool');summary['descriptive']=desc.to_dict('records')
    phase=f.assign(phase=np.where(f.post==1,'post','pre')).groupby(['time_class','phase']).agg(n=('rating','size'),players=('player','nunique'),mean=('rating','mean'),median=('rating','median'),score=('score','mean')).reset_index();output(phase,'pre_post')
    daily=f.groupby(['date','time_class']) # weekly count with fixed 7-day exposure bins
    counts=f.groupby(['event_week','time_class']).size().unstack(fill_value=0)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for c in counts:
        axs[0].plot(counts.index,counts[c],label=c,color=COLORS[c]);axs[1].plot(counts.index,counts[c]/counts.sum(axis=1)*100,label=c,color=COLORS[c])
    for ax in axs:ax.axvline(0,color='#333333',ls='--');ax.set_xlabel('Event week (10 Sep 2020 = week 0)')
    axs[0].set(ylabel='Focal game observations',title='Weekly activity by rating pool');axs[1].set(ylabel='Share of focal observations (%)',title='Pool composition of observed activity');axs[0].legend();save('01_activity')
    fig,axs=plt.subplots(1,3,figsize=(11,3.7))
    for ax,c in zip(axs,('bullet','blitz','rapid')):
        for post,label in ((0,'Before 10 Sep'),(1,'On / after 10 Sep')):
            vals=f[(f.time_class==c)&(f.post==post)].rating
            ax.hist(vals,bins=np.arange(1000,3601,100),density=True,histtype='step',label=label,lw=1.8)
        ax.set(title=c.capitalize(),xlabel='Published post-game rating',ylabel='Probability density')
    axs[0].legend(fontsize=10);save('02_distributions')
    weekly=f.groupby(['player','time_class','event_week'],as_index=False).rating.mean()
    fig,ax=plt.subplots(figsize=(9,4))
    for c in ('bullet','blitz','rapid'):
        a=weekly[weekly.time_class==c].groupby('event_week').rating.agg(['mean','count','std'])
        ax.plot(a.index,a['mean'],marker='o',ms=3,color=COLORS[c],label=c)
    ax.axvline(0,color='#333333',ls='--');ax.set(title='Mean rating with equal weight for each active player-week',xlabel='Event week',ylabel='Published post-game rating');ax.legend();save('03_rating_trends')
    specs=[]
    settings=[('All blitz; balanced; >=3 games','all',3,True,None,False,False),
              ('Exclude 10|0; balanced; >=3 games','no600',3,True,None,False,False),
              ('3|0 only; balanced; >=3 games','180',3,True,None,False,False),
              ('5|0 only; balanced; >=3 games','300',3,True,None,False,False),
              ('All blitz; unbalanced; >=3 games','all',3,False,None,False,False),
              ('All blitz; balanced; >=1 game','all',1,True,None,False,False),
              ('All blitz; balanced; +/-6 weeks','all',3,True,6,False,False),
              ('All blitz; differential linear trend','all',3,True,None,True,False),
              ('All blitz; game-count weighted','all',3,True,None,False,True)]
    primary=None
    for name,control,minimum,balanced,window,trend,weights in settings:
        pp=panel(f,control,minimum,balanced,window);row,fit=did(pp,name,trend,weights)
        if row:specs.append(row)
        if primary is None and fit is not None:primary=pp;summary['primary']=row
    p_all=panel(f,'all');p_180=panel(f,'180')
    common=set(p_all.player)&set(p_180.player)
    for pp,name in [(p_all,'Common players: all blitz'),(p_180,'Common players: 3|0 only')]:
        row,fit=did(pp[pp.player.isin(common)],name)
        if row:specs.append(row)
    specs=pd.DataFrame(specs);output(specs,'did_specifications');primary.to_csv(CLEAN/'primary_player_pool_week.csv',index=False)
    fig,ax=plt.subplots(figsize=(10,5.1)); y=np.arange(len(specs))
    ax.errorbar(specs.estimate,y,xerr=[specs.estimate-specs.ci_low,specs.ci_high-specs.estimate],fmt='o',color=COLORS['bullet'],capsize=3)
    ax.set_yticks(y,specs.specification,fontsize=11);ax.invert_yaxis();ax.axvline(150,color='#444444',ls='--',label='Announced +150');ax.axvline(0,color='#888888',lw=.8);ax.set(title='Estimated bullet shift depends on control and panel construction',xlabel='Difference-in-differences estimate (rating points)');ax.legend();save('04_did_sensitivity')
    events,pre_p=eventstudy(primary);output(events,'event_study');summary['pretrend_p']=pre_p
    fig,ax=plt.subplots(figsize=(9,4.6));ax.errorbar(events.event_week,events.estimate,yerr=[events.estimate-events.ci_low,events.ci_high-events.estimate],fmt='o-',color=COLORS['bullet'],capsize=2)
    ax.axvline(0,color='#333333',ls='--');ax.axhline(0,color='#888888',lw=.8);ax.axhline(150,color='#999999',ls=':');ax.set(title='Bullet versus blitz: event-study contrasts',xlabel='Event week; reference = week -1; week 0 omitted',ylabel='Relative rating difference (points)');save('05_event_study')
    # Paired player-level contrasts, making the weighting and independent units explicit.
    collapse=primary.groupby(['player','pool','post']).rating.mean().unstack(['pool','post']).dropna()
    changes=pd.DataFrame({'player':collapse.index,'bullet_change':collapse[('bullet',1)]-collapse[('bullet',0)],'blitz_change':collapse[('control',1)]-collapse[('control',0)]})
    changes['did']=changes.bullet_change-changes.blitz_change;output(changes,'player_level_changes')
    rng=np.random.default_rng(20201011);boot=np.mean(rng.choice(changes.did.to_numpy(),size=(10000,len(changes)),replace=True),axis=1)
    summary['paired_bootstrap']={'n_players':len(changes),'estimate':changes.did.mean(),'ci_low':float(np.quantile(boot,.025)),'ci_high':float(np.quantile(boot,.975))}
    fig,axs=plt.subplots(1,2,figsize=(10,4));axs[0].scatter(changes.blitz_change,changes.bullet_change,color=COLORS['bullet'],alpha=.8)
    lim=[min(changes.blitz_change.min(),changes.bullet_change.min())-30,max(changes.blitz_change.max(),changes.bullet_change.max())+30]
    axs[0].plot(lim,lim,color='#888888',ls=':');axs[0].set(xlabel='Within-player blitz change (points)',ylabel='Within-player bullet change (points)',title='Paired changes across policy periods')
    axs[1].hist(changes.did,bins=12,color=COLORS['bullet'],alpha=.8);axs[1].axvline(150,color='#333333',ls='--');axs[1].set(xlabel='Player-specific bullet minus blitz change',ylabel='Number of players',title='Heterogeneity across matched players');save('06_player_changes')
    # Turnover decomposition: naive game-weighted vs equal player balanced changes.
    decomp=[]
    for c in ('bullet','blitz','rapid'):
        sub=f[f.time_class==c];a=sub.groupby(['player','post']).rating.mean().unstack().dropna()
        pre=sub[sub.post==0];post=sub[sub.post==1]
        decomp.append({'pool':c,'pooled_game_weighted_change':post.rating.mean()-pre.rating.mean(),
                       'balanced_equal_player_change':(a[1]-a[0]).mean(),'balanced_players':len(a),
                       'pre_players':pre.player.nunique(),'post_players':post.player.nunique()})
    dc=pd.DataFrame(decomp);output(dc,'composition_contrasts');summary['composition']=decomp
    fig,ax=plt.subplots(figsize=(8,4));x=np.arange(len(dc));ax.bar(x-.18,dc.pooled_game_weighted_change,.36,label='All observations: game weighted',color=COLORS['blitz']);ax.bar(x+.18,dc.balanced_equal_player_change,.36,label='Both periods: equal player weight',color=COLORS['bullet']);ax.set_xticks(x,dc.pool);ax.axhline(0,color='#888888',lw=.8);ax.set(title='Changing participation alters the apparent rating shift',xlabel='Rating pool',ylabel='Post minus pre rating (points)');ax.legend(fontsize=11);save('07_composition')
    tc=f.groupby(['time_control','post']).size().unstack(fill_value=0).reset_index();tc.columns=['time_control','pre','post'];output(tc,'time_control_counts')
    summary['ten_minute']={'unique_games':int((df.time_control=='600').sum()),'class_counts':df[df.time_control=='600'].groupby(['time_class','post']).size().reset_index(name='n').to_dict('records')}
    # First bullet observation after the announcement: includes ordinary game updates.
    trans=f[(f.time_class=='bullet')&(f.post==1)&f.prev_rating.notna()&(pd.to_datetime(f.prev_end,unit='s',utc=True)<POLICY)].copy()
    trans['days_after']=(trans.date-POLICY).dt.total_seconds()/86400;output(trans[['player','date','rating_change','score','days_after','gap_hours']],'policy_crossing_transitions')
    summary['transitions']={'n':len(trans),'median_change':float(trans.rating_change.median()),'mean_change':float(trans.rating_change.mean()),'median_days_after':float(trans.days_after.median())}
    fig,axs=plt.subplots(1,2,figsize=(10,4));axs[0].scatter(trans.days_after,trans.rating_change,c=trans.score,cmap='cividis',vmin=0,vmax=1);axs[0].axhline(150,color='#333333',ls='--');axs[0].set(title='First observed bullet game after 10 September',xlabel='Days after announcement',ylabel='Change since prior observed bullet game (points)');axs[1].hist(trans.rating_change,bins=12,color=COLORS['bullet']);axs[1].axvline(150,color='#333333',ls='--');axs[1].set(title='Policy-crossing changes include game outcomes',xlabel='Observed rating change (points)',ylabel='Number of players');save('08_rollout')
    # Outcome model: descriptive only; endpoint ratings are post-game measurements.
    decisive=df[df.white_score!=.5].copy();decisive['white_win']=decisive.white_score.astype(int);decisive['gap100']=decisive.rating_gap/100
    outcome=smf.glm('white_win ~ gap100 + C(time_class) + post + gap100:post',data=decisive,family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':decisive.pair},use_t=True)
    oc=pd.DataFrame({'term':outcome.params.index,'coefficient':outcome.params.values,'se':outcome.bse.values,'pvalue':outcome.pvalues.values,'ci_low':outcome.conf_int()[0].values,'ci_high':outcome.conf_int()[1].values});output(oc,'retrospective_outcome_logit')
    summary['outcome']={'n':len(decisive),'pairs':decisive.pair.nunique(),'gap100':float(outcome.params['gap100']),'post_interaction':float(outcome.params['gap100:post']),'post_interaction_p':float(outcome.pvalues['gap100:post'])}
    bins=pd.cut(decisive.rating_gap,np.arange(-650,651,100));cal=decisive.groupby(bins,observed=True).agg(gap=('rating_gap','mean'),win=('white_win','mean'),n=('white_win','size')).reset_index(drop=True);cal=cal[cal.n>=20];output(cal,'postgame_gap_outcome')
    fig,ax=plt.subplots(figsize=(8,4.5));ax.plot(cal.gap,cal.win,'o-',color=COLORS['blitz'],label='Observed decisive-game White win fraction');xs=np.arange(-600,601);ax.plot(xs,1/(1+10**(-xs/400)),color='#777777',ls='--',label='Elo-shaped reference curve');ax.set(title='Post-game ratings are associated with outcomes',xlabel='Published White minus Black post-game rating',ylabel='White win fraction among decisive games');ax.legend(fontsize=11);save('09_retrospective_association')
    # Rematch audit: reconstruct both ratings from the previous same-pair/same-pool game.
    a=df.sort_values(['pair','time_class','end_time']).copy();gg=a.groupby(['pair','time_class'])
    for col in ('white','black','white_rating','black_rating','end_time'):a['prior_'+col]=gg[col].shift()
    a['prior_wr']=np.where(a.white==a.prior_white,a.prior_white_rating,a.prior_black_rating)
    a['prior_br']=np.where(a.black==a.prior_black,a.prior_black_rating,a.prior_white_rating)
    a['start_stamp']=pd.to_datetime(a.start_time,utc=True).map(lambda t:t.timestamp())
    a['rematch_gap_seconds']=a.start_stamp-a.prior_end_time
    obs=pd.concat([df[['game_id','time_class','end_time','white']].rename(columns={'white':'player'}),df[['game_id','time_class','end_time','black']].rename(columns={'black':'player'})]).sort_values(['player','time_class','end_time','game_id'])
    obs['prior_observed_end']=obs.groupby(['player','time_class']).end_time.shift()
    lookup=dict(zip(zip(obs.game_id,obs.player),obs.prior_observed_end))
    a['prior_observed_white']=[lookup[(g,p)] for g,p in zip(a.game_id,a.white)]
    a['prior_observed_black']=[lookup[(g,p)] for g,p in zip(a.game_id,a.black)]
    adjacent=(a.prior_observed_white==a.prior_end_time)&(a.prior_observed_black==a.prior_end_time)
    rm=a[adjacent&(a.rematch_gap_seconds>=0)&(a.rematch_gap_seconds<=300)&(a.white_score!=.5)].copy()
    rm['lag_gap']=rm.prior_wr-rm.prior_br;rm['y']=rm.white_score.astype(int);rm['delta_gap']=rm.rating_gap-rm.lag_gap
    rm.to_csv(CLEAN/'adjacent_rematches.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    # Fixed Elo-shaped reference, paired sample; no fitted train/test claim.
    preds={name:1/(1+10**(-rm[col].to_numpy()/400)) for name,col in [('postgame','rating_gap'),('lagged_rematch','lag_gap')]}
    losses={name:-(rm.y.to_numpy()*np.log(np.clip(p,1e-9,1-1e-9))+(1-rm.y.to_numpy())*np.log(np.clip(1-p,1e-9,1-1e-9))) for name,p in preds.items()}
    metrics=[]
    for name,p in preds.items():metrics.append({'rating_source':name,'n':len(rm),'accuracy':float(np.mean((p>=.5)==rm.y.to_numpy())),'brier':float(np.mean((p-rm.y.to_numpy())**2)),'log_loss':float(np.mean(losses[name]))})
    output(pd.DataFrame(metrics),'rematch_leakage_metrics');summary['leakage_metrics']=metrics
    rm['loss_difference']=losses['lagged_rematch']-losses['postgame']
    pairloss=rm.groupby('pair').loss_difference.mean();bs=np.mean(rng.choice(pairloss.to_numpy(),size=(10000,len(pairloss)),replace=True),axis=1)
    summary['leakage_paired']={'pairs':len(pairloss),'equal_pair_logloss_gain':float(pairloss.mean()),'ci_low':float(np.quantile(bs,.025)),'ci_high':float(np.quantile(bs,.975)), 'median_update_white_win':float(rm[rm.y==1].delta_gap.median()),'median_update_black_win':float(rm[rm.y==0].delta_gap.median())}
    fig,axs=plt.subplots(1,2,figsize=(10,4));vals=[rm[rm.y==0].delta_gap,rm[rm.y==1].delta_gap];axs[0].boxplot(vals,tick_labels=['Black wins','White wins'],showfliers=False);axs[0].axhline(0,color='#888888',lw=.8);axs[0].set(title='The final rating gap contains the current outcome',xlabel='Result of current rematch',ylabel='Post-game minus lagged gap (points)');axs[1].bar(['Post-game\ninformation','Prior rematch\ninformation'],[m['log_loss'] for m in metrics],color=[COLORS['bullet'],COLORS['blitz']]);axs[1].set(title='Same games, fixed rating-to-probability curve',xlabel='Rating measurement used',ylabel='Mean log loss (lower is better)');save('10_leakage_audit')
    # Descriptive duration and outcomes.
    rates=df.groupby('time_class').agg(n=('game_id','size'),draw_rate=('white_score',lambda s:(s==.5).mean()),white_score=('white_score','mean'),moves_median=('moves_proxy','median')).reset_index();output(rates,'unique_game_descriptive')
    fig,axs=plt.subplots(1,2,figsize=(10,4));axs[0].bar(rates.time_class,rates.draw_rate*100,color=[COLORS[c] for c in rates.time_class]);axs[0].set(title='Draw frequency varies across time controls',xlabel='Rating pool',ylabel='Draws as share of unique games (%)');axs[1].boxplot([df[df.time_class==c].moves_proxy.dropna() for c in ('bullet','blitz','rapid')],tick_labels=['bullet','blitz','rapid'],showfliers=False);axs[1].set(title='Game length from PGN move counters',xlabel='Rating pool',ylabel='Last full-move number (proxy)');save('11_game_characteristics')
    # Schematic based on the exact invariance of pairwise rating differences.
    fig,axs=plt.subplots(1,2,figsize=(10,4));ratings=np.array([1200,1600,2000,2400,2800]);axs[0].plot(ratings,ratings,'o-',label='Original ratings',color=COLORS['blitz']);axs[0].plot(ratings,ratings+150,'o-',label='Uniform +150 rebase',color=COLORS['bullet']);axs[0].set(title='A common offset changes levels',xlabel='Original rating (illustrative)',ylabel='Displayed rating (illustrative)');axs[0].legend(fontsize=11)
    gap=np.linspace(-600,600,100);p=1/(1+10**(-gap/400));axs[1].plot(gap,p,color=COLORS['blitz'],lw=3,label='Before rebase');axs[1].plot(gap,p,color=COLORS['bullet'],ls='--',label='Both players +150');axs[1].set(title='A common offset preserves rating differences',xlabel='Player A minus player B rating',ylabel='Elo-shaped expected score');axs[1].legend(fontsize=11);save('12_rebase_invariance')
    # Pre-period placebo breaks, deliberately exploratory.
    placebo=[]
    prepanel=primary[primary.event_week<0].copy()
    for cutoff in (-10,-8,-6,-4):
        q=prepanel.copy();q['post']=(q.event_week>=cutoff).astype(int);q['treat']=q.bullet*q.post
        row,fit=did(q,f'Pre-period placebo: week {cutoff}')
        if row:row['cutoff']=cutoff;placebo.append(row)
    output(pd.DataFrame(placebo),'placebo_dates');summary['placebos']=placebo
    # Causal structure diagram: policy, skill, participation and measured rating.
    fig,ax=plt.subplots(figsize=(10,4.4));ax.set_xlim(0,10);ax.set_ylim(0,4);ax.axis('off')
    nodes={'policy':(1.4,3.1,'Rating-policy\nannouncement'),'offset':(5,3.1,'Mechanical\nrating offset'),
           'rating':(8.6,2,'Published\npost-game rating'),'skill':(1.4,1,'Underlying skill\nand other shocks'),
           'selection':(5,1,'Participation /\nopponent mix'),'result':(8.6,.45,'Game result')}
    for key,(x,y,label) in nodes.items():ax.text(x,y,label,ha='center',va='center',bbox={'boxstyle':'round,pad=0.5','facecolor':'#f4f6f8','edgecolor':'#aab6c0'},fontsize=10)
    for s,t in [('policy','offset'),('offset','rating'),('policy','selection'),('skill','selection'),('skill','result'),('selection','rating'),('selection','result'),('result','rating')]:
        x,y,_=nodes[s];xx,yy,_=nodes[t];ax.annotate('',xy=(xx,yy),xytext=(x,y),arrowprops={'arrowstyle':'->','color':'#677783','shrinkA':40,'shrinkB':42,'connectionstyle':'arc3,rad=0.08'})
    ax.set_title('Why a rating jump does not identify a skill improvement',pad=15);save('13_causal_structure')
    summary['specifications']=specs.to_dict('records');summary['unique_game_descriptive']=rates.to_dict('records')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=='__main__':main()
