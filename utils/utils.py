import csv
import random
import time
from typing import TypedDict

import requests

import models
from setup_logger import log

Seed = TypedDict('Seed', {'seed': str, 'size': str})


def pick_random_seed(server: models.Server) -> Seed:
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

    time.sleep(1)
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

    time.sleep(1)
    log.debug(f'Getting map url for map id: "{map_id}"')
    response = requests.get(f'https://rustmaps.com/api/v2/maps/{map_id}', headers=headers)
    log.debug(response)

    # check if the key "imageIconUrl" doesn't exist in the response JSON
    data = response.json()
    if "imageIconUrl" not in data:
        return None
    return data['imageIconUrl']


def get_random_map_from_filter(config: models.Config, rustmaps_filter: str) -> Seed:
    headers = {
        'accept': 'application/json',
        'X-API-Key': config.rustmaps_api_token,
    }

    fallback_seeds = [
        {'seed': '1627427312', 'size': '3500'},
        {'seed': '7816705', 'size': '3500'},
        {'seed': '407850846', 'size': '3500'},
        {'seed': '365024044', 'size': '3500'},
        {'seed': '227225294', 'size': '3500'},
        {'seed': '177920335', 'size': '3500'},
        {'seed': '879401911', 'size': '3500'},
        {'seed': '55164153', 'size': '3500'},
        {'seed': '1193750862', 'size': '3500'},
        {'seed': '1319093308', 'size': '3500'},
        {'seed': '1283872140', 'size': '3500'},
        {'seed': '455146133', 'size': '3500'},
    ]

    fallback_seed = random.choice(fallback_seeds)

    params = {
        'page': '0',
    }

    time.sleep(1)
    log.debug(f'Getting random RustMaps map from filter: "{rustmaps_filter}"')
    response = requests.get(f'https://rustmaps.com/api/v2/maps/filter/{rustmaps_filter}', params=params,
                            headers=headers)

    data = response.json()

    if "results" not in data:
        log.debug(f'Failed to get random RustMaps map from filter: "{rustmaps_filter}" - falling back to random seed')
        return fallback_seed

    seeds = data['results']

    if len(seeds) <= 0:
        log.debug(f'No seeds found for filter: "{rustmaps_filter}" - falling back to random seed')
        return fallback_seed

    random_seed = random.choice(seeds)

    seed = Seed(seed=random_seed['seed'], size=random_seed['size'])
    log.debug(f"Picked seed: {seed['seed']} - size: {seed['size']}")

    return seed
