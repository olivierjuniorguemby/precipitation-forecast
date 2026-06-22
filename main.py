import os
import requests

url = os.getenv("APPS_SCRIPT_URL")

token = os.getenv("APPS_SCRIPT_TOKEN")

payload = {

    "date": date_jour,

    "NO1": round(no1, 1),

    "NO2": round(no2, 1),

    "NO3": round(no3, 1),

    "NO4": round(no4, 1),

    "NO5": round(no5, 1),

    "pluieJ15": round(pluie_j15, 1)

}

response = requests.post(
    f"{url}?token={token}",
    json=payload,
    timeout=60
)

print(response.text)

response.raise_for_status()
