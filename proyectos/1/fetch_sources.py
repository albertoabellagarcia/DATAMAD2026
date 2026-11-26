import urllib.request,concurrent.futures
from pathlib import Path
base=Path('inputs')
base.mkdir(exist_ok=True)
urls={'archive.csv':'https://datos.madrid.es/dataset/201200-0-calidad-aire-horario/resource/201200-1-calidad-aire-horario-csv/download/201200-1-calidad-aire-horario-csv.csv','live.json':'https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/calair_tiemporeal.json?pageSize=5000','recent.json':'https://ciudadesabiertas.madrid.es/dynamicAPI/API/query/calair_tiemporeal_ult.json?pageSize=5000'}
def run(it):
 n,u=it
 try:
  r=urllib.request.urlopen(urllib.request.Request(u,headers={'Origin':'http://127.0.0.1:8765'}),timeout=90);b=r.read();(base/n).write_bytes(b);return(n,len(b),r.headers.get('Access-Control-Allow-Origin'),r.geturl(),b[:120])
 except Exception as e:return(n,str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:
 for x in e.map(run,urls.items()):print(x,flush=True)
