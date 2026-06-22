import os
import json
import base64
import requests
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo


REGIONS = {
    "NO1": {"lat": 61.1153, "lon": 10.4662, "poids": 0.07},
    "NO2": {"lat": 59.5610, "lon": 7.3560, "poids": 0.39},
    "NO3": {"lat": 62.5748, "lon": 11.3842, "poids": 0.10},
    "NO4": {"lat": 66.9000, "lon": 15.3000, "poids": 0.24},
    "NO5": {"lat": 60.6290, "lon": 6.4220, "poids": 0.20},
}


def recuperer_precipitation_15_jours(lat, lon):
    url = "https://api.open-meteo.com/v1/ecmwf"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "forecast_days": 15,
        "models": "ecmwf_ifs",
        "timezone": "Europe/Paris"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    precipitations = hourly.get("precipitation", [])

    if not times or not precipitations:
        raise Exception("Aucune donnée météo reçue")

    df = pd.DataFrame({
        "time": pd.to_datetime(times),
        "precipitation": precipitations
    })

    total_15_jours = df["precipitation"].sum()

    return round(float(total_15_jours), 1)


def calculer_payload():
    date_jour = datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y")

    resultats = {
        "date": date_jour
    }

    pluie_j15 = 0

    for region, infos in REGIONS.items():
        valeur = recuperer_precipitation_15_jours(
            infos["lat"],
            infos["lon"]
        )

        resultats[region] = valeur
        pluie_j15 += valeur * infos["poids"]

    resultats["Pluie J+15"] = round(pluie_j15, 1)

    return resultats


def envoyer_json_vers_repo(payload):
    token = os.environ["UPDATER_REPO_TOKEN"]
    owner = os.environ["UPDATER_REPO_OWNER"]
    repo = os.environ["UPDATER_REPO_NAME"]

    file_path = "data.json"

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    get_response = requests.get(api_url, headers=headers, timeout=60)
    get_response.raise_for_status()

    current_file = get_response.json()
    sha = current_file["sha"]

    json_content = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2
    )

    encoded_content = base64.b64encode(
        json_content.encode("utf-8")
    ).decode("utf-8")

    update_payload = {
        "message": f"Update precipitation data {payload['date']}",
        "content": encoded_content,
        "sha": sha
    }

    put_response = requests.put(
        api_url,
        headers=headers,
        json=update_payload,
        timeout=60
    )

    put_response.raise_for_status()

    print("JSON mis à jour dans le repo GitHub")
    print(json_content)


if __name__ == "__main__":
    payload = calculer_payload()
    envoyer_json_vers_repo(payload)
