from pathlib import Path
import csv,json,datetime
out=Path('dist');payload=json.loads((out/'data.json').read_text());known={s['id'] for s in payload['stations']};codes={8,9,10,14};archive_end=''
with Path('inputs/archive.csv').open(encoding='utf-8-sig') as f:
 for r in csv.DictReader(f,delimiter=';'):
  if int(r['MUNICIPIO'])!=79 or int(r['MAGNITUD']) not in codes:continue
  sid=r['PUNTO_MUESTREO'].split('_')[0]
  if sid not in known:raise ValueError('Unknown archive station '+sid)
  date=f"{int(r['ANO']):04}-{int(r['MES']):02}-{int(r['DIA']):02}"
  archive_end=max(archive_end,date)
  if not date.startswith('2026'):continue
  a=[]
  for h in range(1,25):
   try:v=float(r[f'H{h:02}'].replace(',','.'))
   except ValueError:v=-1
   a.append(v if r[f'V{h:02}'].strip()=='V' and v>=0 else None)
  payload['records'].setdefault(sid,{}).setdefault(date,{})[r['MAGNITUD']]=a
payload['archiveEnd']=archive_end;payload['dataYears']=[2025,2026];payload['archiveRetrievedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'data.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False))
x=json.loads(Path('inputs/recent.json').read_text());(out/'recent-snapshot.json').write_text(json.dumps(x,separators=(',',':')))
print('archiveEnd',archive_end,'stations',len(known),'recent records',len(x['records']))
