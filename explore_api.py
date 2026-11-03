import requests, json

BASE = "https://api.fda.gov/drug/event.json"
MONTH = "receivedate:[20250101 TO 20250131]"

# 1) Pull 3 sample reports
r = requests.get(BASE, params={"search": MONTH, "limit": 3}, timeout=30)
r.raise_for_status()
data = r.json()

print("Total reports in Jan 2025:", data["meta"]["results"]["total"])
report = data["results"][0]
print("\nTop-level fields:", list(report.keys()))
print("Patient fields:", list(report["patient"].keys()))

# 2) Drugs and reactions in one report
for d in report["patient"]["drug"]:
    print("DRUG:", d.get("medicinalproduct"), "| role:", d.get("drugcharacterization"))
for rx in report["patient"]["reaction"]:
    print("REACTION:", rx.get("reactionmeddrapt"))

# 3) Save one full report to inspect
with open("sample_report.json", "w") as f:
    json.dump(report, f, indent=2)

# 4) Top 10 reactions that month
top = requests.get(BASE, params={
    "search": MONTH,
    "count": "patient.reaction.reactionmeddrapt.exact",
    "limit": 10}, timeout=30).json()["results"]
print("\nTop 10 reactions:")
for t in top:
    print(f"  {t['term']}: {t['count']}")