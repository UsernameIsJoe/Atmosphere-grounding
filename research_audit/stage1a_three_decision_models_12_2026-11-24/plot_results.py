#!/usr/bin/env python3
"""Render exact saved distributions and separate sensitivity measurements."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')
COLORS=('#a5b0c0','#078595','#ca522d','#7956b7')
LABELS=('Neither','Support only','Opposition only','Both')
NEW=('mammoth','karpo','glide')
DISPLAY={'mammoth':'Mammoth-1','karpo':'Karpo 31B','glide':'GLiDE 27B'}


def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':'#17263f','axes.labelcolor':'#536580',
                          'xtick.color':'#536580','ytick.color':'#536580','axes.edgecolor':'#d5deeb',
                          'figure.facecolor':'#f6f8fc','axes.facecolor':'#f6f8fc'})
    cases=list(csv.DictReader((ROOT/'case_probability_comparison.csv').open()))
    bycase={(r['model'],r['case_id']):r for r in cases}
    decider=json.loads((ROOT/'decider_baseline.json').read_text())['cases']
    baseline=json.loads((ROOT/'baseline_vectors.json').read_text())['cases']
    fig,axes=plt.subplots(2,2,figsize=(14,10.2));fig.subplots_adjust(left=.12,right=.98,top=.83,bottom=.18,wspace=.37,hspace=.43)
    subjects=[('K01','Personal wedding-logistics stress'),('K05','Owner yelling'),('K06','Street / watching children'),('U06','Comfortable seating / music')]
    for ax,(case,title) in zip(axes.flat,subjects):
        vectors=[baseline[case]['qwen_semantic_order_mean'],baseline[case]['gemma_T4_mapping_mean'],decider[case]]
        names=['Qwen semantic','Gemma T=4','Decider v1.2']
        for model in NEW:
            r=bycase[model,case];vectors.append({s:float(r[s]) for s in STATES});names.append(DISPLAY[model])
        q=np.array([[v[s]*100 for s in STATES] for v in vectors]);left=np.zeros(len(q));y=np.arange(len(q))
        for i,(s,color) in enumerate(zip(STATES,COLORS)):
            ax.barh(y,q[:,i],left=left,color=color,height=.68,edgecolor='#f6f8fc',linewidth=.8)
            for j in range(len(q)):
                if q[j,i]>=18:ax.text(left[j]+q[j,i]/2,j,f'{q[j,i]:.1f}%',ha='center',va='center',color='white' if i else '#17263f',fontweight='bold',fontsize=10)
            left+=q[:,i]
        ax.set_yticks(y,names);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100],[f'{x}%' for x in [0,25,50,75,100]])
        ax.set_title(f'{case} · {title}',loc='left',fontweight='bold',pad=12)
        ax.set_axisbelow(True);ax.xaxis.grid(True,color='#dce3ee');ax.tick_params(axis='both',length=0)
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.04,.95,'Decision-model probability comparison',fontsize=23,fontweight='bold')
    fig.text(.04,.905,'Calm only · original wording · mean of four semantic-aligned option variants',fontsize=13,color='#536580')
    fig.legend([Patch(color=c,label=l) for c,l in zip(COLORS,LABELS)],LABELS,loc='lower center',bbox_to_anchor=(.5,.105),ncol=4,frameon=False)
    fig.text(.04,.065,'Saved Qwen / Gemma / Decider baselines; three new native runs. Gemma T=4 is illustrative, not a fitted calibration.',fontsize=10,color='#536580')
    fig.text(.04,.035,'Different wrappers, attention and scoring temperatures: numerical confidence is not established as comparable across models.',fontsize=10,color='#536580')
    fig.savefig(ROOT/'four_case_probability_comparison.png',dpi=160);plt.close(fig)

    summary=json.loads((ROOT/'summary.json').read_text())['models']
    fig,axes=plt.subplots(1,2,figsize=(13,5.8));fig.subplots_adjust(left=.12,right=.98,top=.73,bottom=.22,wspace=.45)
    common_max=max(summary[m][field]['maximum_review_gap_pp'] for m in NEW for field in ['primary_order_sensitivity','wording_sensitivity_after_order_averaging'])*1.2+1
    for ax,(field,title) in zip(axes,[('primary_order_sensitivity','Native option order'),('wording_sensitivity_after_order_averaging','Equivalent task wording')]):
        y=np.arange(3);med=[summary[m][field]['median_review_gap_pp'] for m in NEW];worst=[summary[m][field]['maximum_review_gap_pp'] for m in NEW]
        ax.barh(y-.16,med,height=.29,color='#078595',label='Median across 12 targets');ax.barh(y+.16,worst,height=.29,color='#ca522d',label='Maximum across 12 targets')
        for yy,v in zip(y-.16,med):ax.text(v+.35,yy,f'{v:.2f}',va='center',fontsize=10)
        for yy,v in zip(y+.16,worst):ax.text(v+.35,yy,f'{v:.2f}',va='center',fontsize=10)
        ax.set_yticks(y,[DISPLAY[m] for m in NEW]);ax.invert_yaxis();ax.set_xlim(0,common_max)
        ax.set_title(title,loc='left',fontweight='bold');ax.set_xlabel('Largest state-probability range (percentage points)')
        ax.xaxis.grid(True,color='#dce3ee');ax.set_axisbelow(True);ax.tick_params(length=0)
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.04,.92,'Two kinds of presentation sensitivity',fontsize=22,fontweight='bold')
    fig.text(.04,.855,'Option order: four cyclic native orders. Wording: three instruction versions after averaging those orders.',fontsize=11,color='#536580')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.09),ncol=2,frameon=False)
    fig.text(.04,.04,'Definitions, codebook and review text stay fixed. These changes are separate from identical-input repeatability.',fontsize=10,color='#536580')
    fig.savefig(ROOT/'order_and_wording_sensitivity.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
