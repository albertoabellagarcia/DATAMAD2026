from pathlib import Path
import io,zipfile,json
import numpy as np
import pandas as pd
BASE=Path(__file__).resolve().parent/'inputs'
OUT=Path(__file__).parent/'dist'
SRC=BASE/'historical'
CODES=[1,8,9,10,14]
def read(b):
 for enc in ['utf-8-sig','latin-1']:
  try:
   d=pd.read_csv(io.BytesIO(b),sep=';',encoding=enc);break
  except UnicodeDecodeError: pass
 d.columns=d.columns.str.strip().str.lower().str.replace('ñ','n')
 return d

def load(year):
 p=SRC/f'{year}.zip'
 if p.exists():
  with zipfile.ZipFile(p) as z:
   d=pd.concat([read(z.read(n)) for n in z.namelist() if n.lower().endswith('.csv') and '__MACOSX' not in n],ignore_index=True)
 else: d=read((SRC/f'{year}.csv').read_bytes())
 d=d[d.municipio.eq(79)&d.magnitud.isin(CODES)].copy().reset_index(drop=True)
 d['id']=d.punto_muestreo.astype(str).str.split('_').str[0]
 d['date']=pd.to_datetime(dict(year=d.ano,month=d.mes,day=d.dia)).dt.strftime('%Y-%m-%d')
 vals=np.column_stack([pd.to_numeric(d[f'h{h:02}'].astype(str).str.replace(',','.'),errors='coerce').to_numpy(float) for h in range(1,25)])
 valid=np.column_stack([d[f'v{h:02}'].astype(str).str.strip().str.upper().eq('V').to_numpy() for h in range(1,25)])
 vals[~valid|~np.isfinite(vals)|(vals<0)]=np.nan
 assert not d.duplicated(['id','date','magnitud']).any(),f'Duplicates {year}'
 return d[['id','date','magnitud']],vals

def clean(v):
 a=pd.DataFrame(v)
 a=a[a.notna().sum(axis=1)>=22]
 return a.T.interpolate(limit=2,limit_area='inside').T.dropna()

def kmeans(x,k=3):
 rng=np.random.default_rng(42);best=None
 for trial in range(5):
  c=x[rng.choice(len(x),k,replace=False)].copy()
  for _ in range(60):
   lab=((x[:,None,:]-c[None,:,:])**2).sum(2).argmin(1)
   new=np.array([x[lab==i].mean(0) if (lab==i).any() else x[rng.integers(len(x))] for i in range(k)])
   if np.allclose(c,new):break
   c=new
  score=((x-c[lab])**2).sum()
  if best is None or score<best[0]:best=(score,lab)
 return best[1]

def groups(raw,shape=None,dates=None):
 std=raw.std(1);good=std>0;raw=raw[good]
 if len(raw)<30:return None
 if shape is None: shape=(raw-raw.mean(1)[:,None])/raw.std(1)[:,None]
 else:shape=shape[good]
 labs=kmeans(shape)
 out=[]
 for i in range(3):
  sel=labs==i
  if sel.sum()<5:continue
  a=raw[sel]
  out.append({'n':int(sel.sum()),'peakMedian':round(float(np.median(a.max(1))),2),'peakLo':round(float(np.quantile(a.max(1),.25)),2),'peakHi':round(float(np.quantile(a.max(1),.75)),2),'median':np.median(a,0).round(2).tolist(),'lo':np.quantile(a,.25,axis=0).round(2).tolist(),'hi':np.quantile(a,.75,axis=0).round(2).tolist(),'shape':np.median(shape[sel],0).round(5).tolist()})
 return out or None

meta,vals=load(2025)
records={}
for (sid,date,code),v in zip(meta.itertuples(index=False,name=None),vals):
 records.setdefault(sid,{}).setdefault(date,{})[str(code)]=[None if not np.isfinite(x) else float(x) for x in v]
print('2025 loaded',len(meta),flush=True)
hm=[];hv=[]
for year in range(2015,2026):
 m,v=load(year);a=clean(v);hm.append(m.loc[a.index].reset_index(drop=True));hv.append(a.to_numpy());print(year,len(a),flush=True)
hm=pd.concat(hm,ignore_index=True);hv=np.concatenate(hv)
hm['month']=hm.date.str[5:7].astype(int)
profiles={};shared={}
for code in CODES:
 shared[str(code)]={}
 for month in range(1,13):
  ids=np.flatnonzero(hm.magnitud.eq(code)&hm.month.eq(month))
  frame=hm.iloc[ids]
  for sid,part in frame.groupby('id'):
   g=groups(hv[part.index.to_numpy()])
   if g:profiles.setdefault(sid,{}).setdefault(str(code),{})[str(month)]=g
  # Shared shape: one daily profile across stations, retained only when median pairwise correlation >= .60.
  shapes=[];rawdays=[];memberdays=[]
  for date,part in frame.groupby('date'):
   a=hv[part.index.to_numpy()];a=a[a.std(1)>0]
   if len(a)<5:continue
   z=(a-a.mean(1)[:,None])/a.std(1)[:,None]
   corr=np.corrcoef(z);pairs=corr[np.triu_indices(len(a),1)]
   if np.median(pairs)<.6:continue
   common=np.median(z,0)
   if common.std()==0:continue
   shapes.append((common-common.mean())/common.std());rawdays.append(np.median(a,0));memberdays.append(a)
  if len(shapes)>=30:
   labels=kmeans(np.array(shapes));gs=[]
   for k in range(3):
    ix=np.flatnonzero(labels==k)
    if len(ix)<5:continue
    a=np.concatenate([memberdays[i] for i in ix])
    gs.append({'n':len(ix),'stationDays':len(a),'peakMedian':round(float(np.median(a.max(1))),2),'peakLo':round(float(np.quantile(a.max(1),.25)),2),'peakHi':round(float(np.quantile(a.max(1),.75)),2),'median':np.median(a,0).round(2).tolist(),'lo':np.quantile(a,.25,axis=0).round(2).tolist(),'hi':np.quantile(a,.75,axis=0).round(2).tolist(),'shape':np.median(np.array(shapes)[ix],0).round(5).tolist()})
   if gs:shared[str(code)][str(month)]=gs
 print('profiles',code,flush=True)
st=read((BASE/'stations.csv').read_bytes())
stations=[{'id':str(r.estacion_codigo),'name':r.estacion_nome,'lat':float(r.estacion_coord_latitud),'lon':float(r.estacion_coord_longitud),'type':r.estacion_tipo_estacion} for r in st.itertuples() if str(r.estacion_codigo) in records]
payload={'stations':stations,'records':records,'profiles':profiles,'shared':shared,'history':'2015–2025','dataYear':2025,'sources':{'data':'https://datos.madrid.es/dataset/201200-0-calidad-aire-horario','eea':'https://airindex.eea.europa.eu/AQI/'}}
if (OUT/'data.json').exists():
 previous=json.loads((OUT/'data.json').read_text())
 payload={**previous,**payload,'records':previous['records'],'stations':previous['stations']}
payload['historyStart']=2015;payload['historyEnd']=2025
OUT.mkdir(exist_ok=True);(OUT/'data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False))
print('saved',len(stations),'stations',min(meta.date),max(meta.date),flush=True)
