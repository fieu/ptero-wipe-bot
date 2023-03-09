import random
import threading
import time
from typing import Union

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
from rich import inspect, print
from rich.traceback import install

import models
from models import Config
from setup_logger import log
from utils import ptero, utils

install(show_locals=True)


def send_prompt():
    return input("> ")


def main(command):
    log.info('STARTED')
    with open("config.json", "r") as f:
        config_json_str = f.read()
    config = Config.from_json(config_json_str)

    # Verify each server exists on the host
    log.info("Getting servers...")
    for host in config.hosts:
        # Global Ptoerdactyl headers
        headers = {
            "Authorization": f"Bearer {host.api_token}",
            "Content-Type": "application/json",
            "Accept": "Application/vnd.pterodactyl.v1+json",
        }

        response = requests.get(f"{host.url}/api/client", headers=headers)
        data = response.json()

        # Check if each server id exists in Pterodactyl server list JSON
        for server in host.servers:
            if any(s["attributes"]["identifier"] == server.id for s in data["data"]):
                log.info(
                    f'Server "{server.id}" - "{server.name}" found on host "{host.name}"'
                )
            else:
                log.error(
                    f'Server "{server.id}" - "{server.name}" not found on host "{host.name}". Check config.json file.'
                )
                exit(1)

    log.info("Commands:")
    log.info("wipe <server id> - Wipes server")

    for host in config.hosts:
        if " " not in command and command != "quit":
            if command != "":
                log.error("Usage: wipe <server id>")
            break

        server = None
        # Split args via space character
        args = command.split(" ")
        # trim all arguments
        args = [arg.strip() for arg in args]
        # if argument is empty, remove it
        args = [arg for arg in args if arg != ""]
        if len(args) < 1:
            log.error("Usage: wipe <server id>")
        log.info(f"Command arguments: {args}")
        if args[0]:
            if args[0] == "quit":
                log.info("Exiting...")
                exit(0)
            if args[0] == "wipe":
                if len(args) <= 1:
                    if command == "":
                        log.error("Usage: wipe <server id>")
                    break
                server_id = args[1]
                # find server in any host that corresponds to server_id
                for h in config.hosts:
                    for s in h.servers:
                        if s.id == server_id:
                            server = s
                            break
                    if server:
                        break
                if not server:
                    log.error(f'Server "{server_id}" not found in config.json')
                    break
                log.info(f'Found server "{server.name}" - ID: "{server.id}"')

            # Global Ptoerdactyl headers
            # "host" must be equal to a host which holds the correct "server_id"
            for h in config.hosts:
                for s in h.servers:
                    if s.id == server.id:
                        host = h
                        break
            headers = {
                "Authorization": f"Bearer {host.api_token}",
                "Content-Type": "application/json",
                "Accept": "Application/vnd.pterodactyl.v1+json",
            }
            log.info(
                f'Starting wipe process for server "{server.name}" - ID: "{server.id}"'
            )
            log.info(f"Saving server")
            if not ptero.send_command(host, server, "save"):
                log.warning(f'Failed to send "save" comment to server')
            time.sleep(2)
            log.info(f"Stopping server")
            if not ptero.stop_server(host, server):
                log.warning(f"Failed to stop server (Maybe it's already stopped?)")
            else:
                log.info(f"Stopped server")

            time.sleep(3)

            status = "unset"
            # if status is not "offline", keep requesting until it is
            while status != "offline":
                response = requests.get(
                    f"{host.url}/api/client/servers/{server.id}/resources",
                    headers=headers,
                )
                status = response.json()["attributes"]["current_state"]
                if status == "offline":
                    log.debug(f'ID: "{server.id}" - Server status: "{status}"')
                else:
                    log.debug(
                        f'ID: "{server.id}" - Server status: "{status}" (waiting for "offline" status)'
                    )
                time.sleep(1)

            log.info(f"Server is offline")

            if not ptero.delete_files(host, server, server.files_to_delete):
                log.warning("Failed to delete server files")
            log.info("Deleted server files")

            # Custom map
            custom_map: models.CustomMap | None = None
            if len(server.custom_maps) > 0:
                if server.pick_random_map:
                    custom_map: models.CustomMap = random.choice(server.custom_maps)
                else:
                    # TODO: Figure out how to rotate maps
                    custom_map: models.CustomMap = server.custom_maps[0]
                log.info(f'Using custom map url "{custom_map.map_url}"')
                if not ptero.change_custom_map(host, server, custom_map):
                    log.warning("Failed to change custom map")
                log.info(
                    f"Changed custom map. Map URL: {custom_map.map_url} - Image URL: {custom_map.image_url}"
                )

            # Use procedural
            if server.seeds_file:
                if not custom_map:
                    seed = utils.pick_random_seed(server)
                    if not ptero.change_seed(host, server, seed["seed"], seed["size"]):
                        log.warning("Failed to change seed")
                    log.info(
                        f"Changed seed. Seed: {seed['seed']} - Size: {seed['size']}"
                    )
                    # Submit map generation request to RustMaps.com
                    generated_map_id = utils.generate_rustmaps_map(
                        config, seed["seed"], seed["size"]
                    )
                    if not generated_map_id:
                        log.warning(
                            f'Failed to submit map generation request for seed {seed["seed"]} - size {seed["size"]}'
                        )
                    log.info(
                        f'Submitted map generation request for seed {seed["seed"]} - size {seed["size"]}'
                    )

            # change map really here
            log.info("Starting server")
            if not ptero.start_server(host, server):
                log.warning("Server failed to start")
            log.info("Server started")
            status = "unset"
            while status != "starting":
                response = requests.get(
                    f"{host.url}/api/client/servers/{server.id}/resources",
                    headers=headers,
                )
                status = response.json()["attributes"]["current_state"]
                if status == "starting":
                    log.debug(f'ID: "{server.id}" - Server status: "{status}"')
                else:
                    log.debug(
                        f'ID: "{server.id}" - Server status: "{status}" (waiting for "starting" status)'
                    )
                time.sleep(1)
            log.info(f"Server is now starting")

            def send_discord_webhook(
                host: models.Host,
                server: models.Server,
                custom_map: models.CustomMap = None,
            ):
                webhook = DiscordWebhook(url=server.discord.webhook)
                if server.discord.ping_role:
                    webhook.set_content(f"<@&{server.discord.ping_role}>")
                if server.discord.ping_everyone:
                    webhook.set_content("@everyone")
                embed_description = None
                if not custom_map:
                    embed_description = f"{server.discord.embed.description}\n\n**🗺️ Map Link**\nClick [here](https://rustmaps.com/map/{seed['size']}_{seed['seed']}) to view the map"
                else:
                    embed_description = f"{server.discord.embed.description}\n\n**🗺️ Map Type**\nCustom Map"
                embed = DiscordEmbed(
                    title=f"**{server.name} just wiped!**",
                    description=embed_description,
                )
                if not custom_map:
                    generated_map_url = None
                    while not generated_map_url:
                        log.debug(
                            f'ID: "{server.id}" - Waiting for generated map image url for seed {seed["seed"]} - size {seed["size"]}'
                        )
                        generated_map_url = utils.get_generated_map_url(
                            config, generated_map_id
                        )
                        if generated_map_url:
                            embed.set_image(url=generated_map_url)
                            log.debug(
                                f'ID: "{server.id}" - Retrieved generated map image url "{generated_map_url[:25] + "..."}"'
                            )
                if custom_map:
                    embed.set_image(url=custom_map.image_url)
                if not custom_map:
                    embed.add_embed_field(
                        name="🌱 Seed", value=f"```{seed['seed']}```", inline=True
                    )
                    embed.add_embed_field(
                        name="📏 Size", value=f"```{seed['size']}```", inline=True
                    )
                embed.add_embed_field(
                    name="🖥️ Connect",
                    value=f"```{server.connect_address}```",
                    inline=False,
                )
                embed.add_embed_field(
                    name="🔗 Direct Join",
                    value=f"steam://connect/{server.connect_address}",
                    inline=False,
                )
                embed.set_color(server.discord.embed.color[1:])
                webhook.add_embed(embed)
                # wait until server is "running", then send webhook
                status = "unset"
                running_count = 1
                while status != "running":
                    response = requests.get(
                        f"{host.url}/api/client/servers/{server.id}/resources",
                        headers=headers,
                    )
                    status = response.json()["attributes"]["current_state"]
                    if running_count % 5 == 0:
                        if status == "running":
                            log.debug(f'ID: "{server.id}" - Server status: "{status}"')
                        else:
                            log.debug(
                                f'ID: "{server.id}" - Server status: "{status}" (waiting for "running" status)'
                            )
                    time.sleep(1)
                    running_count = running_count + 1
                log.info(f"\nServer {server.name} is now running. Sending webhook...")

                webhook_resp = webhook.execute()
                if webhook_resp.status_code != 200:
                    log.warning(
                        f"Failed to send webhook. Status code: {webhook_resp.status_code}"
                    )
                else:
                    log.info(f"Sent Discord webhook")
                    log.info(
                        f'Wipe complete for server "{server.name}" - ID: "{server.id}"'
                    )

            if custom_map:
                webhook_thread = threading.Thread(
                    target=send_discord_webhook,
                    args=(
                        host,
                        server,
                        custom_map,
                    ),
                    daemon=True,
                )
            else:
                webhook_thread = threading.Thread(
                    target=send_discord_webhook,
                    args=(
                        host,
                        server,
                    ),
                    daemon=True,
                )
            webhook_thread.start()
            break


if __name__ == "__main__":
    try:
        command = ""
        count = 0
        while True:
            if count < 1:
                count = count + 1
                main(command)
            else:
                command = input("> ")
                main(command)
    except KeyboardInterrupt:
        log.info("Exiting...")

# hosts = [Host.from_json(json.dumps(h)) for h in config_json['hosts']]

# hosts: Hosts = Hosts.from_json(json.dumps(config_json))
