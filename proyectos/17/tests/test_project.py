import csv,json,threading,unittest
from urllib.request import urlopen
from pathlib import Path
from http.server import ThreadingHTTPServer
import app
from src import weather

class ProjectTests(unittest.TestCase):
 def rows(self,path):
  with (app.ROOT/path).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
 def test_municipalities(self):
  rows=self.rows('data/processed/municipios.csv')
  self.assertEqual(len(rows),179);self.assertEqual(len({r['cod_ine'] for r in rows}),179)
 def test_events(self):
  rows=self.rows('sources/egif/partes_madrid.csv')
  self.assertEqual({y:sum(r['anio']==str(y) for r in rows) for y in range(2020,2024)},{2020:242,2021:314,2022:295,2023:201})
 def test_probabilities(self):
  rows=self.rows('results/ocurrencia_mensual.csv')
  self.assertEqual(len(rows),179*12)
  self.assertTrue(all(0<=float(r['probabilidad'])<=1 for r in rows))
 def test_scenarios(self):
  rows=self.rows('results/escenarios.csv')
  self.assertEqual(len(rows),179*12*3)
 def test_path_security(self):
  self.assertIsNone(app.public_file('/../app.py'))
  self.assertIsNone(app.public_file('/web/../../app.py'))
 def test_weather_empty(self):
  result=weather.snapshot(cache={'schema':1,'locations':{}})
  self.assertEqual(len(result['dates']),7);self.assertEqual(result['locations'],{})
 def test_http(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for path in ['/','/web/app.js','/web/science.js','/api/weather','/results/ocurrencia_mensual.csv']:
    with urlopen('http://127.0.0.1:'+str(server.server_port)+path) as r:
     self.assertEqual(r.status,200);r.read()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
