import os
import json
import base64
import requests
from datetime import datetime, timedelta
from calendar import monthrange
from zoneinfo import ZoneInfo


REGIONS = {
    "NO1": {"latitude": 61.1153, "longitude": 10.4662, "poids": 0.06880733944954129},
    "NO2": {"latitude": 59.5610, "longitude": 7.3560, "poids": 0.3887614678899083},
    "NO3": {"latitude": 62.5748, "longitude": 11.3842, "poids": 0.10435779816513763},
    "NO4": {"latitude": 66.9000, "longitude": 15.3000, "poids": 0.23853211009174316},
    "NO5": {"latitude": 60.6290, "longitude": 6.4220, "poids": 0.19954128440366972}
}


REF_P_MENSUEL = {
    1: 147.8476490825688,
    2: 119.78024655963303,
    3: 82.76541571100918,
    4: 48.34010894495414,
    5: 70.45533256880734,
    6: 84.17302178899084,
    7: 107.45086009174312,
    8: 138.34294724770643,
    9: 110.70260894495414,
    10: 133.33689793577983,
    11: 100.81967889908259,
    12: 128.44888188073395
}


def recuperer_total_precipitation_15_jours(region, latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation",
        "models": "ecmwf_ifs",
        "forecast_days": 15,
        "timezone": "Europe/Paris"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    precipitations = data["hourly"]["precipitation"]

    total = sum(v for v in precipitations if v is not None)

    return round(total, 1)


def calculer_ref_p_m(date_execution):
    total_ref = 0

    for i in range(1, 16):
        date_jour = date_execution + timedelta(days=i)

        mois = date_jour.month
        annee = date_jour.year

        nb_jours_mois = monthrange(annee, mois)[1]
        ref_mois = REF_P_MENSUEL[mois]

        total_ref += ref_mois / nb_jours_mois

    return round(total_ref, 1)


def generer_payload():
    date_execution = datetime.now(ZoneInfo("Europe/Paris"))

    payload = {
        "date": date_execution.strftime("%d/%m/%Y")
    }

    for region, infos in REGIONS.items():
        payload[region] = recuperer_total_precipitation_15_jours(
            region,
            infos["latitude"],
            infos["longitude"]
        )

    pluie_j15 = (
        payload["NO1"] * REGIONS["NO1"]["poids"]
        + payload["NO2"] * REGIONS["NO2"]["poids"]
        + payload["NO3"] * REGIONS["NO3"]["poids"]
        + payload["NO4"] * REGIONS["NO4"]["poids"]
        + payload["NO5"] * REGIONS["NO5"]["poids"]
    )

    payload["Pluie J+15"] = round(pluie_j15, 1)

    payload["Ref_P/m"] = calculer_ref_p_m(date_execution)

    if payload["Ref_P/m"] != 0:
        payload["Ecart en %"] = round(
            (payload["Pluie J+15"] - payload["Ref_P/m"]) / payload["Ref_P/m"],
            4
        )
    else:
        payload["Ecart en %"] = 0

    return payload


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

    json_content = json.dumps(payload, ensure_ascii=False, indent=2)

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

    print("data.json mis à jour avec succès")
    print(json_content)


if __name__ == "__main__":
    payload = generer_payload()
    envoyer_json_vers_repo(payload)
