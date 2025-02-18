import configparser
import logging
from pathlib import Path


config = configparser.ConfigParser()

# Path to config.ini
config_file = Path("config.ini")
if not config_file.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file}")

# Read config.ini
config.read(config_file)
logger = logging.getLogger(__name__)

# main.py
APP_NAME = config.get("general", "app_name", fallback="CodeReviewAI")
RESPONSE_REQUIRED_KEYS = {"Solutions", "Skills", "Rating"}

debug_level = config.get("general", "debug", fallback="INFO")
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
DEBUG_LEVEL = LOG_LEVELS.get(debug_level.upper(), logging.INFO)

# services.py
GITHUB_ROOT = config.get("services", "github_root", fallback="https://github.com/")
GITHUB_API_URL = config.get("services", "github_api_url", fallback="https://api.github.com")

DEFAULT_BATCH_SIZE = 7
DEFAULT_MIN_MAX_BATCH_SIZE = (2, 100)
# BATCH_SIZE = config.getint("services", "butch_size", fallback=7)
try:
    batch_size = config.getint("services", "butch_size", fallback=DEFAULT_BATCH_SIZE)
    if batch_size < DEFAULT_MIN_MAX_BATCH_SIZE[0] or batch_size > DEFAULT_MIN_MAX_BATCH_SIZE[1]:
        logging.error("Invalid batch_size in config.ini: %s. Using default: ", DEFAULT_BATCH_SIZE)
        BATCH_SIZE = DEFAULT_BATCH_SIZE
    else:
        BATCH_SIZE = batch_size
except configparser.NoSectionError:
    logging.error("Config section 'services' not found in config.ini. Using default: ", DEFAULT_BATCH_SIZE)
    BATCH_SIZE = DEFAULT_BATCH_SIZE
except configparser.NoOptionError:
    logging.error("Option 'batch_size' not found in section 'services'. Using default: ", DEFAULT_BATCH_SIZE)
    BATCH_SIZE = DEFAULT_BATCH_SIZE


DEFAULT_VALID_EXTENSIONS = {".py", ".md", ".ini"}  # Default valid file extensions
try:
    file_extensions = set(config.get("services", "valid_extensions").split(","))
    invalid_extensions = {ext for ext in file_extensions if not ext.startswith(".")}
    if invalid_extensions:
        logging.error(
            "Invalid file extensions in config.ini: %s. Using default VALID_EXTENSIONS.",
            ", ".join(invalid_extensions)
        )
        VALID_EXTENSIONS = DEFAULT_VALID_EXTENSIONS
    else:
        VALID_EXTENSIONS = file_extensions
except configparser.NoSectionError:
    logging.error("Config section 'services' not found in config.ini. Using default VALID_EXTENSIONS.")
    VALID_EXTENSIONS = DEFAULT_VALID_EXTENSIONS
except configparser.NoOptionError:
    logging.error("Option 'valid_extensions' not found in section 'services'. Using default VALID_EXTENSIONS.")
    VALID_EXTENSIONS = DEFAULT_VALID_EXTENSIONS


# api_requests.py

DEFAULT_VALID_MODELS = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4-turbo"]
DEFAULT_GPT_MODEL = 'gpt-3.5-turbo'
try:
    gpt_model = config.get("api_requests", "model", fallback=DEFAULT_GPT_MODEL).lower().strip()
    if gpt_model not in DEFAULT_VALID_MODELS:
        logging.error(
            "Invalid gpt model in config.ini: %s. Using default 'gpt-3.5-turbo'.", "Valid gpt models: "
            ", ".join(DEFAULT_VALID_MODELS)
        )
        GPT_MODEL = DEFAULT_GPT_MODEL
    else:
        GPT_MODEL = gpt_model
except configparser.NoSectionError:
    logging.error("Config section 'api_requests' not found in config.ini. Using default: ", DEFAULT_GPT_MODEL)
    GPT_MODEL = DEFAULT_GPT_MODEL
except configparser.NoOptionError:
    logging.error("Option 'model' not found in section 'api_requests'. Using default: ", DEFAULT_GPT_MODEL)
    GPT_MODEL = DEFAULT_GPT_MODEL

DEFAULT_MAX_TOKENS = 400
DEFAULT_TOTAL_MAX_TOKENS = 4000
# MAX_TOKENS = config.getint("api_requests", "max_tokens", fallback=400)
try:
    max_tokens = config.getint("api_requests", "max_tokens", fallback=400)
    if max_tokens < 40:
        logging.error("Less than 40. Invalid max_tokens in config.ini: %s. Using default '400'.")
        MAX_TOKENS = DEFAULT_MAX_TOKENS
    elif max_tokens > DEFAULT_TOTAL_MAX_TOKENS:
        logging.error("More than 4000. Invalid max_tokens in config.ini: %s. Using default '400'.")
        MAX_TOKENS = DEFAULT_MAX_TOKENS
    elif DEFAULT_TOTAL_MAX_TOKENS // BATCH_SIZE < max_tokens:
        max_tokens = DEFAULT_TOTAL_MAX_TOKENS // BATCH_SIZE
        logging.error("More than max tokens in batch_size. Invalid max_tokens in config.ini: %s. Using: ", max_tokens)
        MAX_TOKENS = max_tokens
    else:
        MAX_TOKENS = max_tokens
except configparser.NoSectionError:
    logging.error("Config section 'api_requests' not found in config.ini. Using: ", DEFAULT_MAX_TOKENS)
    MAX_TOKENS = DEFAULT_MAX_TOKENS
except configparser.NoOptionError:
    logging.error("Option 'max_tokens' not found in section 'api_requests'. Using: ", DEFAULT_MAX_TOKENS)
    MAX_TOKENS = DEFAULT_MAX_TOKENS

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MIN_MAX_TEMPERATURE = (0, 1)
# TEMPERATURE = config.getfloat("api_requests", "temperature", fallback=0.7)
try:
    temperature = config.getfloat("api_requests", "temperature", fallback=DEFAULT_TEMPERATURE)
    if temperature < DEFAULT_MIN_MAX_TEMPERATURE[0] or temperature > DEFAULT_MIN_MAX_TEMPERATURE[1]:
        logging.error("Invalid temperature in config.ini: %s. Using default: ", DEFAULT_TEMPERATURE)
        TEMPERATURE = DEFAULT_TEMPERATURE
    else:
        TEMPERATURE = temperature
except configparser.NoSectionError:
    logging.error("Config section 'api_requests' not found in config.ini. Using default: ", DEFAULT_TEMPERATURE)
    TEMPERATURE = DEFAULT_TEMPERATURE
except configparser.NoOptionError:
    logging.error("Option 'temperature' not found in section 'api_requests'. Using default: ", DEFAULT_TEMPERATURE)
    TEMPERATURE = DEFAULT_TEMPERATURE
