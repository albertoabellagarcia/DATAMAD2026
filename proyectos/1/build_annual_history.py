"""Build small annual summaries using the app's aggregation rules."""
from pathlib import Path
import json, subprocess
scope={'__file__':str(Path('prepare_data.py').resolve())}
exec(Path('prepare_data.py').read_text().split('meta,vals=load(2025)')[0],scope)
np=scope['np']; previous={}; result={}
import os
node=os.environ.get('NODE_BINARY','node')
js="""const fs=require('fs'),vm=require('vm');const input=JSON.parse(fs.readFileSync(0,'utf8'));const ctx=vm.createContext({console});vm.runInContext(fs.readFileSync('dist/app.js','utf8').replace(/init\\(\\);\\s*$/,''),ctx);ctx.input=input;const result=vm.runInContext(`D={records:input.records};Object.fromEntries(input.stations.map(id=>[id,Object.fromEntries([8,9,10,14].map(c=>[c,{...annualStats(id,input.year+'-12-31',24,c),...(c===9?{daily:annualStats(id,input.year+'-12-31',24,10,9,25)}:{})}]))]))`,ctx);process.stdout.write(JSON.stringify(result));"""
for year in range(2015,2026):
 meta,vals=scope['load'](year); records={}
 for (sid,date,code),v in zip(meta.itertuples(index=False,name=None),vals):
  if code==1:continue
  records.setdefault(sid,{}).setdefault(date,{})[str(code)]=[None if not np.isfinite(x) else float(x) for x in v]
 stations=list(records)
 for sid,days in previous.items():
  for date,values in days.items():
   if date.endswith('-12-31'):records.setdefault(sid,{})[date]=values
 output=subprocess.run([node,'-e',js],input=json.dumps({'records':records,'stations':stations,'year':year}),text=True,capture_output=True,check=True)
 result[str(year)]=json.loads(output.stdout);previous=records
 print(year,len(stations),flush=True)
Path('dist/annual-history.json').write_text(json.dumps(result,separators=(',',':')))
