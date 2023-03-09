import logging

from rich.logging import RichHandler

from models import Config

with open('config.json', 'r') as f:
    config_json_str = f.read()
config = Config.from_json(config_json_str)

# Setup logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.basicConfig(level=config.log_level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
log = logging.getLogger("rich")