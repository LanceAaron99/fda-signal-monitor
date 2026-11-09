import os, time, requests
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
BASE = "https://api.fda.gov/drug/event.json"
KEY = os.getenv("FDA_API_KEY")

drugs = pd.read_sql("SELECT DISTINCT drug FROM signals", engine)["drug"].tolist()
print(f"Fetching indications for {len(drugs):,} drugs...")

rows = []
for i, drug in enumerate(drugs, 1):
    name = drug.replace('"', '')
    params = {"search": f'patient.drug.openfda.generic_name.exact:"{name}"',
              "count": "patient.drug.drugindication.exact",
              "limit": 10, "api_key": KEY}
    r = None
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=30)
            if r.status_code in (200, 404):
                break
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    if r is not None and r.status_code == 200:
        for item in r.json()["results"]:
            rows.append({"drug": drug, "indication": item["term"], "n": item["count"]})
    if i % 200 == 0:
        print(f"  {i:,} / {len(drugs):,} done")
    time.sleep(0.3)   # stay well under the API rate limit

out = pd.DataFrame(rows)
out.to_csv("drug_indications.csv", index=False)   # backup in case the upload fails
out.to_sql("drug_indications", engine, if_exists="replace", index=False)
print(f"Saved {len(out):,} drug-indication rows ✅")