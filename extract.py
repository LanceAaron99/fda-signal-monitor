import os, time, requests
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.fda.gov/drug/event.json"
API_KEY = os.getenv("FDA_API_KEY")
PAGE_SIZE = 1000  # max records per call

def get_page(day, skip):
    """Get one page of reports, retrying patiently if the API hiccups."""
    params = {"search": f"receivedate:[{day} TO {day}]",
              "limit": PAGE_SIZE, "skip": skip}
    if API_KEY:
        params["api_key"] = API_KEY
    r = None
    for attempt in range(5):
        try:
            r = requests.get(BASE, params=params, timeout=60)
        except requests.RequestException:
            r = None                       # network blip, try again
        else:
            if r.status_code == 404:       # no reports that day
                return None
            if r.status_code == 200:
                return r.json()
            if r.status_code not in (429, 500, 502, 503, 504):
                break                      # real error, don't retry
        time.sleep(5 * (attempt + 1))      # wait 5s, 10s, 15s, 20s, 25s
    status = r.status_code if r is not None else "no response"
    raise RuntimeError(f"FDA API failed for {day} (skip={skip}): {status}")

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