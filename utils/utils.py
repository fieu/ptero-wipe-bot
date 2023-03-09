import csv
import random

import requests

import models
from setup_logger import log


def pick_random_seed(server: models.Server) -> dict:
    with open(f'seeds/{server.seeds_file}', 'r') as file:
        csv_reader = csv.DictReader(file)
        seed = random.choice(list(csv_reader))
        log.debug(f"Picked seed: {seed['seed']} - size: {seed['size']}")
        return seed


def generate_rustmaps_map(config: models.Config, seed: str, size: str) -> str | None:
    headers = {
        'accept': 'application/json',
        'X-API-Key': config.rustmaps_api_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    params = {
        'staging': 'false',
        'barren': 'false',
    }

    log.debug(f'Submitting map generation request for seed: {seed} - size: {size}')
    response = requests.post(f'https://rustmaps.com/api/v2/maps/{seed}/{size}', params=params, headers=headers)
    log.debug(response)

    if response.status_code != 200 and response.status_code != 204 and response.status_code != 409:
        log.debug(response)
        log.debug(response.json())
        return None
    data = response.json()
    return data['mapId']


def get_generated_map_url(config: models.Config, map_id: str):
    headers = {
        'accept': 'application/json',
        'X-API-Key': config.rustmaps_api_token,
    }

    log.debug(f'Getting map url for map id: {map_id}')
    response = requests.get(f'https://rustmaps.com/api/v2/maps/{map_id}', headers=headers)
    log.debug(response)

    # check if the key "imageIconUrl" doesn't exist in the response JSON
    data = response.json()
    if "imageIconUrl" not in data:
        return None
    return data['imageIconUrl']
