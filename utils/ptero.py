import fnmatch
import time
from typing import List

import requests
from discord_webhook import DiscordWebhook
from rich import inspect, print

import models
from setup_logger import log


def send_command(host: models.Host, server: models.Server, command: str) -> bool:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }

    time.sleep(1)
    log.debug(
        f'Sending command: "{command}" to server: "{server.name}" - ID: "{server.id}"'
    )
    response = requests.post(
        f"{host.url}/api/client/servers/{server.id}/command",
        headers=headers,
        json={"command": command},
    )
    if response.status_code == 204:
        return True
    else:
        return False


def delete_files(
    host: models.Host, server: models.Server, file_list: List[str]
) -> bool:
    matched_files = []

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }

    # file_list: List[models.PteroFile] = []
    file_paths: List[str] = []

    for file in file_list:
        directory = f"{file.rsplit('/', 1)[0]}/"
        time.sleep(1)
        log.debug(
            f'Getting file list for directory: {directory} on server: "{server.name}" - ID: "{server.id}"'
        )
        response = requests.get(
            f"{host.url}/api/client/servers/{server.id}/files/list?directory={directory}",
            headers=headers,
        )
        for file_data in response.json()["data"]:
            file_name = file_data["attributes"]["name"]
            file_paths.append(f"{directory}{file_name}")
        break

    for file_path in file_paths:
        for pattern in file_list:
            if fnmatch.fnmatch(file_path, pattern):
                log.debug(f"Matched {pattern} with {file_path}")
                matched_files.append(file_path)
                break

    for file in matched_files:
        log.info(f"Matched file: {file}")

    json_data = {
        "root": "/",
        "files": matched_files,
    }

    time.sleep(1)
    log.debug(
        f'Deleting files: {matched_files} on server: "{server.name}" - ID: "{server.id}"'
    )
    response = requests.post(
        f"{host.url}/api/client/servers/{server.id}/files/delete",
        headers=headers,
        json=json_data,
    )

    if response.status_code == 422:
        log.warn(f"No files matched for deletion.")
        return False

    if response.status_code != 204:
        return False
    return True


def stop_server(host: models.Host, server: models.Server) -> bool:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }
    time.sleep(1)
    log.debug(f'Stopping server: "{server.name}" - ID: "{server.id}"')
    response = requests.post(
        f"{host.url}/api/client/servers/{server.id}/power",
        headers=headers,
        json={"signal": "stop"},
    )
    if response.status_code != 204:
        return False
    return True


def start_server(host: models.Host, server: models.Server) -> bool:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }
    time.sleep(1)
    log.debug(f'Starting server: "{server.name}" - ID: "{server.id}"')
    response = requests.post(
        f"{host.url}/api/client/servers/{server.id}/power",
        headers=headers,
        json={"signal": "start"},
    )
    if response.status_code != 204:
        return False
    return True


def change_seed(host: models.Host, server: models.Server, seed: str, size: str) -> bool:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }
    time.sleep(1)
    log.debug(f'Changing seed to "{seed}" and world size to "{size}')
    response = requests.put(
        f"{host.url}/api/client/servers/{server.id}/startup/variable",
        headers=headers,
        json={"key": "WORLD_SIZE", "value": size},
    )
    if response.status_code != 200:
        log.error(f'Failed to change world size to "{size}"')
        return False
    log.debug(f'Changed world size to "{size}"')
    time.sleep(1)
    log.debug(f'Changing seed to "{seed}"')
    response = requests.put(
        f"{host.url}/api/client/servers/{server.id}/startup/variable",
        headers=headers,
        json={"key": "WORLD_SEED", "value": seed},
    )

    if response.status_code != 200:
        log.error(f'Failed to change seed to "{seed}"')
        return False
    log.debug(f'Changed seed to "{seed}"')
    return True


def change_custom_map(
    host: models.Host, server: models.Server, custom_map: models.CustomMap
):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {host.api_token}",
    }
    time.sleep(1)
    log.debug(f"Changing map url to {custom_map.map_url}.")
    response = requests.put(
        f"{host.url}/api/client/servers/{server.id}/startup/variable",
        headers=headers,
        json={"key": "MAP_URL", "value": custom_map.map_url},
    )
    if response.status_code != 200:
        log.error(f"Failed to change map url to {custom_map.map_url}")
        return False
    log.debug(f"Changed map url to {custom_map.map_url}.")

    return True
