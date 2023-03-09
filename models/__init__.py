from typing import List
from dataclasses import dataclass

from dataclass_wizard import JSONWizard


@dataclass
class PteroFile(JSONWizard):
    name: str
    mode: str
    mode_bits: str
    size: int
    is_file: bool
    is_symlink: bool
    mimetype: str
    created_at: str
    modified_at: str


@dataclass
class CustomMap:
    map_url: str
    image_url: str


@dataclass
class DiscordEmbed:
    description: str
    color: str


@dataclass
class Discord:
    webhook: str
    ping_everyone: bool
    ping_role: int | None
    embed: DiscordEmbed


@dataclass
class Server:
    id: str
    name: str
    connect_address: str
    dont_wipe_on_force_wipe: bool
    discord: Discord
    pick_random_map: True
    seeds_file: str | None
    rustmaps_seeds_filter: str | None
    custom_maps: List[CustomMap]
    files_to_delete: List[str]


@dataclass
class Host(JSONWizard):
    name: str
    url: str
    api_token: str
    servers: List[Server]


@dataclass
class Config(JSONWizard):
    log_level: str
    rustmaps_api_token: str
    hosts: List[Host]
