'''食量智配：校园食堂智能备餐模拟原型。仅使用合成数据，不包含真实校园记录。'''
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)
SEED=20261121
DISHES=['米饭套餐','面食套餐','素食套餐']
FEATURES=['weekday','temperature','rain','event','preorders']
CO,CU=1.0,2.5
ALPHA=CU/(CO+CU)

def generate():
    rng=np.random.default_rng(SEED)
    rows=[]
    for day,date in enumerate(pd.date_range('2026-03-02',periods=168)):
        w=date.weekday(); weekend=w>=5
        temp=round(18+7*np.sin((day-30)/100*np.pi)+rng.normal(0,3),1)
        rain=int(rng.random()<.27); event=int(rng.random()<.16 and not weekend)
        # 模拟午餐需求均值；预订量与需求共享情景，而非由实际需求反推。
        mus=[170-54*weekend+30*event-16*rain+0.7*(temp-20),
             110-28*weekend+20*event+15*rain-1.3*(temp-20),
             77-20*weekend+12*event-4*rain+0.9*(temp-20)]
        common=rng.normal(0,10)
        for j,(dish,mu) in enumerate(zip(DISHES,mus)):
            mu += common
            pre=max(0,round(.36*mu+rng.normal(0,3)))
            actual=max(1,round(mu+rng.normal(0,7)))
            rows.append([day,date.strftime('%Y-%m-%d'),dish,w,temp,rain,event,pre,actual])
    return pd.DataFrame(rows,columns=['day','date','dish',*FEATURES,'demand'])

def metrics(df, method):
    pred=df[method+'_pred']; q=df[method+'_prep']; y=df.demand
    left=(q-y).clip(lower=0); short=(y-q).clip(lower=0)
    return dict(mae=float(mean_absolute_error(y,pred)), wape=float(abs(y-pred).sum()/y.sum()*100),
                prepared=int(q.sum()), demand=int(y.sum()), leftover=int(left.sum()), shortage=int(short.sum()),
                fill=float((1-short.sum()/y.sum())*100), cost=float(CO*left.sum()+CU*short.sum()))

def run():
    # 固定种子重新生成，保证数据可复现；也保存 CSV 供检查。
    data=generate(); data.to_csv(ROOT/'synthetic_data.csv',index=False,encoding='utf-8-sig')
    out=[]; buffers=[]
    for dish in DISHES:
        g=data[data.dish==dish]; tr=g[g.day<112]; cal=g[(g.day>=112)&(g.day<140)].copy(); te=g[g.day>=140].copy()
        means=tr.groupby('weekday').demand.mean()
        rf=RandomForestRegressor(n_estimators=160,max_depth=7,min_samples_leaf=4,random_state=SEED,n_jobs=1)
        rf.fit(tr[FEATURES],tr.demand)
        for d in [cal,te]:
            d['base_pred']=d.weekday.map(means); d['ai_pred']=rf.predict(d[FEATURES])
        for method in ['base','ai']:
            # 独立校准期，同一损失比率；不使用测试需求决定备餐。
            b=float(np.quantile(cal.demand-cal[method+'_pred'],ALPHA))
            te[method+'_prep']=np.maximum(0,np.ceil(te[method+'_pred']+b)).astype(int)
            buffers.append(dict(dish=dish,method=method,buffer=b))
        out.append(te)
    df=pd.concat(out).sort_values(['day','dish']).reset_index(drop=True)
    result={'seed':SEED,'days':168,'train_days':112,'cal_days':28,'test_days':28,'co':CO,'cu':CU,'alpha':ALPHA,'buffers':buffers,'baseline':metrics(df,'base'),'ai':metrics(df,'ai'),'by_dish':{dish:{m:metrics(df[df.dish==dish],m) for m in ['base','ai']} for dish in DISHES}}
    df.to_csv(OUT/'test_predictions.csv',index=False,encoding='utf-8-sig')
    (OUT/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    html=(ROOT/'demo_template.html').read_text(encoding='utf-8').replace('__ROWS__',df.to_json(orient='records',force_ascii=False)).replace('__METRICS__',json.dumps(result,ensure_ascii=False))
    (ROOT/'demo.html').write_text(html,encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return df,result
if __name__=='__main__': run()
