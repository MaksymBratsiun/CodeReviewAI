import configparser
from pathlib import Path

config = configparser.ConfigParser()

# Path to config.ini
config_file = Path("config.ini")
if not config_file.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file}")

# Read config.ini
config.read(config_file)
