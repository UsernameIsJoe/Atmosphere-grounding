"""Analyze completed fixed embedding audit, with review-level dependence respected."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path('research_audit/embedding_representativeness_2026-11-24');d=pd.read_csv(O/'segment_scores.csv');meta=json.loads((O/'manifest.json').read_text());sanity=json.loads((O/'sanity_checks.json').read_text())
d['length_share']=d.words/d.groupby('source_id').words.transform('sum')
d['uniform_weight']=1/d.n_segments
# Relative-to-uniform weights remove the mechanical 1/n review-size effect.
for m in ['qwen','mpnet']: d[m+'_relative_weight']=d[m+'_weight']*d.n_segments
multi=d[d.n_segments>1].copy()
def rho(a,b):
 x=pd.DataFrame({'a':a,'b':b}).dropna()
 return float(spearmanr(x.a,x.b).statistic) if len(x)>2 and x.a.nunique()>1 and x.b.nunique()>1 else None
def within(frame,a,b):
 vals=[rho(g[a],g[b]) for _,g in frame.groupby('source_id') if len(g)>=3]
 vals=[v for v in vals if v is not None and np.isfinite(v)]
 return {'median_rho':float(np.median(vals)) if vals else None,'reviews':len(vals)}
summary={'sample':meta,'sanity':sanity,'models':{}}
for m in ['qwen','mpnet']:
 x=multi.dropna(subset=[m+'_weight']);w=x[m+'_weight'];c=x[m+'_cosine']
 summary['models'][m]={'eligible_multi_reviews':int(x.source_id.nunique()),'eligible_segments':len(x),'raw_cosine_percentiles':dict(zip(['p05','p50','p95'],np.quantile(c,[.05,.5,.95]).tolist())),'pooled_weight_length_rho':rho(w,x.words),'relative_weight_length_rho':rho(x[m+'_relative_weight'],x.words),'within_review_length':within(x,m+'_weight','words'),'within_review_position':within(x,m+'_weight','position'),'within_review_length_share':within(x,m+'_weight','length_share'),'mean_absolute_difference_length_share':float((w-x.length_share).abs().mean()),'mean_absolute_difference_uniform':float((w-x.uniform_weight).abs().mean()),'mean_self_match_inflation':float((c-x[m+'_loo']).mean()),'within_review_full_vs_loo':within(x,m+'_weight',m+'_loo_weight'),'median_full_minus_reversed_cosine':float((c-x[m+'_reversed_cosine']).median()),'within_review_rank_agreement_reversed':within(x,m+'_cosine',m+'_reversed_cosine')}
 # Regress cosine on standardized log length, normalized position and review fixed effects.
 z=x[['source_id','words','position',m+'_cosine']].copy();z['log_words']=np.log1p(z.words)
 cols=['log_words','position',m+'_cosine'];z[cols]=z[cols]-z.groupby('source_id')[cols].transform('mean')
 X=z[['log_words','position']].to_numpy();y=z[m+'_cosine'].to_numpy();coef=np.linalg.lstsq(X,y,rcond=None)[0]
 rng=np.random.default_rng(20261124);ids=z.source_id.unique();boots=[]
 for _ in range(1000):
  b=pd.concat([z[z.source_id==rid] for rid in rng.choice(ids,len(ids),replace=True)],ignore_index=True)
  boots.append(np.linalg.lstsq(b[['log_words','position']].to_numpy(),b[m+'_cosine'].to_numpy(),rcond=None)[0])
 summary['models'][m]['review_fixed_effect_cosine_regression']={'log_length_coefficient':float(coef[0]),'position_coefficient':float(coef[1]),'cluster_bootstrap_95ci':np.quantile(boots,[.025,.975],axis=0).tolist()}
shared=multi.dropna(subset=['qwen_weight','mpnet_weight'])
summary['cross_model']={'shared_multi_reviews':int(shared.source_id.nunique()),'shared_segments':len(shared),'pooled_weight_rho':rho(shared.qwen_weight,shared.mpnet_weight),'relative_weight_rho':rho(shared.qwen_relative_weight,shared.mpnet_relative_weight),'within_review':within(shared,'qwen_weight','mpnet_weight'),'mean_absolute_weight_difference':float((shared.qwen_weight-shared.mpnet_weight).abs().mean())}
(O/'summary.json').write_text(json.dumps(summary,indent=2));d.to_csv(O/'segment_scores.csv',index=False)
fig,ax=plt.subplots(2,3,figsize=(14,8))
for m,color in [('qwen','#247ba0'),('mpnet','#e5963b')]:
 x=multi.dropna(subset=[m+'_weight']);ax[0,0].hist(x[m+'_cosine'],bins=25,alpha=.5,label=m,color=color)
 ax[0,1].scatter(x.words,x[m+'_relative_weight'],s=9,alpha=.4,label=m,color=color)
 ax[0,2].scatter(x.position,x[m+'_relative_weight'],s=9,alpha=.3,label=m,color=color)
 ax[1,1].scatter(x.length_share,x[m+'_weight'],s=9,alpha=.4,label=m,color=color)
 ax[1,2].scatter(x[m+'_loo'],x[m+'_cosine'],s=9,alpha=.4,label=m,color=color)
ax[1,0].scatter(shared.qwen_relative_weight,shared.mpnet_relative_weight,s=12,alpha=.5)
for a,title,xlab,ylab in zip(ax.flat,['Raw cosine compression','Length association','Position association','Cross-model agreement','Length-share baseline','Self-match inflation'],['Cosine','Segment words','Normalized position','Qwen weight × segment count','Length share','Cosine to remainder'],['Segments','Weight × segment count','Weight × segment count','MPNet weight × segment count','Cosine weight','Cosine to full review']):a.set(title=title,xlabel=xlab,ylabel=ylab);a.grid(alpha=.15)
for a in [ax[0,0],ax[0,1],ax[1,1],ax[1,2]]:a.legend()
fig.tight_layout();fig.savefig(O/'diagnostics.png',dpi=180);plt.close(fig)
# Deterministic 20-review audit: cover segment-count quartiles and include short-segment cases.
ids=multi.groupby('source_id').n_segments.first().sort_values();chosen=[]
for rid in np.array_split(ids.index.to_numpy(),4):
 if len(rid):chosen.extend(np.random.default_rng(20261124).choice(rid,min(5,len(rid)),replace=False).tolist())
audit=[]
for rid in chosen:
 g=d[d.source_id==rid].copy();g=g.sort_values('qwen_weight',ascending=False)
 audit.append({'source_id':int(rid),'full_review':g.full_review.iloc[0],'segments':g[['unit_id','text','words','qwen_cosine','qwen_weight','mpnet_weight','length_share']].to_dict('records'),'highest':g.text.iloc[0],'lowest':g.text.iloc[-1]})
(O/'manual_audit_20.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False));print(json.dumps(summary,indent=2))
