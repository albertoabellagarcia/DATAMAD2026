from pathlib import Path
import json
scope={'__file__':str(Path('prepare_data.py').resolve())}
exec(Path('prepare_data.py').read_text().split('meta,vals=load(2025)')[0],scope)
np,pd=scope['np'],scope['pd']; history=json.loads(Path('dist/annual-history.json').read_text()); previous={};checked=0
for year in range(2015,2026):
 meta,values=scope['load'](year); calendar=pd.date_range(f'{year}-01-01',f'{year}-12-31'); nd=len(calendar)
 for sid,stats in history[str(year)].items():
  for code in (8,9,10,14):
   mask=(meta.id==sid)&(meta.magnitud==code); block=pd.DataFrame(values[mask],index=pd.to_datetime(meta.loc[mask,'date'])).reindex(calendar).to_numpy(); valid=np.isfinite(block)
   if code in (8,9):
    n=int(valid.sum()); above=int((block>200).sum()); mean=float(np.nanmean(block)) if n else None
   elif code==10:
    good=valid.sum(1)>=18; n=int(good.sum()); means=np.divide(np.nansum(block,axis=1),valid.sum(1),out=np.zeros(nd),where=valid.sum(1)>0); above=int(((means>50)&good).sum());mean=None
   else:
    prior=previous.get((sid,code),np.full(24,np.nan)); joined=np.concatenate([prior,block.ravel()]); rolling=pd.Series(joined).rolling(8,min_periods=6).mean().to_numpy()[24:].reshape(nd,24);good=np.isfinite(rolling).sum(1)>=18;n=int(good.sum());above=int(((np.nan_to_num(rolling,nan=-1).max(1)>120)&good).sum());mean=None
   st=stats[str(code)];assert st['valid']==n,(year,sid,code,'valid',st['valid'],n);assert st['above']==above,(year,sid,code,'above',st['above'],above)
   if code in (8,9): assert (st['mean'] is None and mean is None) or abs(st['mean']-mean)<1e-8
   assert st['within']+st['above']+st['missing']==st['total']
   if code==9:
    good=valid.sum(1)>=18;means=np.divide(np.nansum(block,axis=1),valid.sum(1),out=np.zeros(nd),where=valid.sum(1)>0);daily=st['daily'];assert daily['valid']==int(good.sum());assert daily['above']==int(((means>25)&good).sum())
   previous[sid,code]=block[-1];checked+=1
 print(year,'verified',flush=True)
print('Independent pandas audit passed:',checked,'station/year/pollutant combinations')
