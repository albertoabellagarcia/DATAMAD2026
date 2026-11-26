"""Estimación mensual condicionada a la temperatura de cada simulación CMIP6."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import brier_score_loss, average_precision_score
ROOT=Path(__file__).resolve().parents[1]
data=ROOT/'data/processed'
out=ROOT/'results'
mun=pd.read_csv(data/'municipios.csv',dtype={'cod_ine':str})
met=pd.read_csv(data/'estaciones_mensuales.csv')
# Mediana de estaciones: aproximación regional consistente ante meses faltantes.
temps=met.groupby(['anio','mes']).tmax_c_media_diaria.median().rename('temperatura')
fires=pd.read_csv(ROOT/'sources/egif/partes_madrid.csv',dtype={'ine':str})
fires['mes']=pd.to_datetime(fires.fecha).dt.month
positive=set(zip(fires.ine,fires.anio,fires.mes))
grid=pd.MultiIndex.from_product([mun.cod_ine,range(2020,2024),range(1,13)],names=['cod_ine','anio','mes']).to_frame(index=False)
grid['y']=[int(tuple(row) in positive) for row in grid.itertuples(index=False,name=None)]
grid=grid.join(temps,on=['anio','mes'])
def fit(frame,C,thermal):
    transforms=[('territorio_calendario',OneHotEncoder(handle_unknown='ignore'),['cod_ine','mes'])]
    if thermal: transforms.append(('temperatura',StandardScaler(),['temperatura']))
    return make_pipeline(ColumnTransformer(transforms),LogisticRegression(C=C,max_iter=1000,tol=1e-8)).fit(frame,frame.y)
records=[]
for thermal in (False,True):
 for c in (.1,1,10):
  for year in (2021,2022,2023):
   test=grid[grid.anio==year]
   model=fit(grid[grid.anio<year],c,thermal)
   prob=model.predict_proba(test)[:,1]
   records.append(dict(temperatura=thermal,C=c,anio=year,brier=brier_score_loss(test.y,prob),ap=average_precision_score(test.y,prob)))
scores=pd.DataFrame(records);scores.to_csv(out/'validacion_campanas.csv',index=False)
chosen=scores[scores.temperatura & (scores.anio<2023)].groupby('C').brier.mean().idxmin()
trained=fit(grid,chosen,True)
climate=pd.read_csv(out/'clima_2027_2030.csv').rename(columns={'maxima_media_c':'temperatura'})
future=mun[['cod_ine']].merge(climate,how='cross')
future['p']=trained.predict_proba(future)[:,1]
summary=future.groupby(['anio','mes','cod_ine']).p.agg(baja='min',central='mean',alta='max')
summary.to_csv(out/'campanas_municipales.csv',float_format='%.8f')
print('C seleccionado',chosen,'beta temperatura estandarizada',trained[-1].coef_[0,-1]);print(scores[(scores.anio==2023)&(scores.C==chosen)])
