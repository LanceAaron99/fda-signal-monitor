import os, requests
from dotenv import load_dotenv

load_dotenv()
r = requests.get("https://api.fda.gov/drug/event.json", params={
    "search": "receivedate:[20250101 TO 20261231]",
    "count": "receivedate",
    "api_key": os.getenv("FDA_API_KEY")}, timeout=60)
r.raise_for_status()

days = sorted(r.json()["results"], key=lambda x: x["time"])
print("Latest date available:", days[-1]["time"])
print("Last 7 days of data:")
for d in days[-7:]:
    print(f"  {d['time']}: {d['count']} reports")