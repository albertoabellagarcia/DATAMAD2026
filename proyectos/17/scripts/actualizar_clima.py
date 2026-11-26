"""Recalcula las 96 filas de proyecciones mensuales de Madrid capital."""
from pathlib import Path
import json,csv,statistics
from urllib.request import urlopen
p=Path(__file__).resolve().parents[1]
URL='https://climate-api.open-meteo.com/v1/climate?latitude=40.42&longitude=-3.70&start_date=2027-01-01&end_date=2030-12-31&models=EC_Earth3P_HR,MRI_AGCM3_2_S&daily=temperature_2m_max,precipitation_sum'
models=['EC_Earth3P_HR','MRI_AGCM3_2_S']
with urlopen(URL, timeout=90) as response:
 data=json.load(response)['daily']
rows=[]
for yr in range(2027,2031):
 for month in range(1,13):
  ix=[i for i,date in enumerate(data['time']) if date.startswith(f'{yr}-{month:02d}')]
  for model in models:
   t=[data['temperature_2m_max_'+model][i] for i in ix]; rain=[data['precipitation_sum_'+model][i] for i in ix]
   rows.append(dict(anio=yr,mes=month,modelo=model,maxima_media_c=round(statistics.mean(t),2),lluvia_mm=round(sum(rain),1),dias_calor=sum(x>=30 for x in t)))
with (p/'results/clima_2027_2030.csv').open('w') as f:
 out=csv.DictWriter(f,fieldnames=rows[0]);out.writeheader();out.writerows(rows)
