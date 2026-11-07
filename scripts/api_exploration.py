import json
import requests
import os

API_KEY = os.environ["EBIRD_API_KEY"]

url = "https://api.ebird.org/v2/data/obs/GB/recent/notable"

headers = {
    "X-eBirdApiToken": API_KEY,
}

params = {
    "back": 1,
    "detail": "full",
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30,
)

response.raise_for_status()

records = response.json()

print(f"Retrieved {len(records)} notable sightings\n")

if records:
    print("Fields:")
    for key in sorted(records[0].keys()):
        print(f"  {key}")

    print("\nFirst record:\n")
    print(json.dumps(records[0], indent=2))

with open("uk_notable.json", "w", encoding="utf-8") as f:
    json.dump(records, f, indent=2)

print("\nSaved to uk_notable.json")