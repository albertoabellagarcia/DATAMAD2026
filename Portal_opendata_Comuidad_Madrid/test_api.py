import requests, csv

RID = "f809ef2a-8385-43a5-87c6-c079d217a658"
BASE = "https://datos.comunidad.madrid/api/3/action"

# 1) Easiest: get the original file's download URL
r = requests.get(f"{BASE}/resource_show", params={"id": RID}).json()
if r.get("success"):
    url = r["result"]["url"]
    print("Direct download:", url)
    with open("dataset_full" + url[url.rfind("."):], "wb") as f:
        f.write(requests.get(url).content)

# 2) Fallback: page through the datastore
rows, offset, limit = [], 0, 5000
while True:
    res = requests.get(f"{BASE}/datastore_search",
                       params={"resource_id": RID, "limit": limit, "offset": offset}).json()
    if not res.get("success"):
        print("Datastore not available:", res.get("error")); break
    batch = res["result"]["records"]
    rows += batch
    total = res["result"]["total"]
    print(f"{len(rows)}/{total}")
    offset += limit
    if not batch or len(rows) >= total:
        break

if rows:
    with open("dataset_full.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)