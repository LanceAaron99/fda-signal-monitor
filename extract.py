import os, time, requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.fda.gov/drug/event.json"
API_KEY = os.getenv("FDA_API_KEY")
PAGE_SIZE = 1000  # max records per call

def get_page(day, skip):
    """Get one page of reports, retrying if the API hiccups."""
    params = {"search": f"receivedate:[{day} TO {day}]",
              "limit": PAGE_SIZE, "skip": skip}
    if API_KEY:
        params["api_key"] = API_KEY
    for attempt in range(3):
        r = requests.get(BASE, params=params, timeout=60)
        if r.status_code == 404:      # no reports that day
            return None
        if r.status_code == 200:
            return r.json()
        time.sleep(2 ** attempt)      # wait 1s, 2s, 4s then retry
    r.raise_for_status()

def fetch_day(day):
    """Pull ALL reports received on one day (format YYYYMMDD)."""
    results, skip = [], 0
    while True:
        data = get_page(day, skip)
        if data is None:
            break
        results.extend(data["results"])
        total = data["meta"]["results"]["total"]
        skip += PAGE_SIZE
        if skip >= total:
            break
        if skip > 25000:              # openFDA's paging limit
            print(f"⚠️ {day}: only got {len(results)} of {total}")
            break
    return results

if __name__ == "__main__":
    day = "20250115"
    reports = fetch_day(day)
    print(f"{day}: pulled {len(reports)} reports ✅")