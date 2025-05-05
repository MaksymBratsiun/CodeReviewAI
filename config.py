import configparser
import logging
from dotenv import load_dotenv
import os
from pathlib import Path

from openai import AsyncOpenAI

load_dotenv()
config = configparser.ConfigParser()

# Path to config.ini
config_file = Path("config.ini")
if not config_file.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file}")

# Read config.ini
config.read(config_file)
logger = logging.getLogger(__name__)

# OPENAI API KEY
try:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Environment variable 'OPENAI_API_KEY' is not set or is empty.")

    client = AsyncOpenAI(api_key=api_key)

except ValueError as ve:
    logger.error(f"Configuration error: {ve}")
    raise

except Exception as e:
    logger.exception("Failed to initialize OpenAI client.")
    raise

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

# BATCH_SIZE = config.getint("services", "butch_size", fallback=7)
DEFAULT_BATCH_SIZE = 7
DEFAULT_MIN_MAX_BATCH_SIZE = (2, 100)
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
# GPT_MODEL = config.get("api_requests", "model", fallback="gpt-3.5-turbo").lower().strip()
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

# MAX_TOKENS = config.getint("api_requests", "max_tokens", fallback=400)
DEFAULT_MAX_TOKENS = 400
DEFAULT_TOTAL_MAX_TOKENS = 4000
try:
    max_tokens = config.getint("api_requests", "max_tokens", fallback=DEFAULT_MAX_TOKENS)
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

# TEMPERATURE = config.getfloat("api_requests", "temperature", fallback=0.7)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MIN_MAX_TEMPERATURE = (0, 1)
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

# Prompt
DEFAULT_PROMPT_USER_STRUCTURE = """
Identifying weaknesses, issues and good solutions code structure in 3 sentences. Make conclusion in 1 sentences.
 """
DEFAULT_PROMPT_USER_FILE_ANALYZE = """
Identifying weaknesses, issues and good solutions in 2-3 sentences. 
Write a brief comment on the developer’s skills in 1 sentence for developer level: 
"""
DEFAULT_PROMPT_USER_TASK = "Make summary review according preview analyze:"
DEFAULT_PROMPT_SOLUTIONS = "Solutions: identifying weaknesses and good solutions in 2-3 sentences."
DEFAULT_PROMPT_SKILLS = "Skills: write a brief comment on the developer’s skills in 1-2 sentence."
DEFAULT_PROMPT_RATING = "Rating: (from 1 to 5) for developer level:"

# f"{PROMPT_SYS}{description}"
DEFAULT_PROMPT_SYS = """
You are an AI assistant reviewing developer code. 
Always provide your responses in the following JSON structure:{"Solutions": "A brief comment about the code weaknesses, 
issues and good solutions.", "Skills": "A concise evaluation of the developer's skills.", "Rating": integer(1..5) } 
Ensure that the response strictly adheres to this format and "Rating" is from 1 to 5. Evaluate the code according:
"""
PROMPT_SYS = config.get("api_requests", "prompt_sys_json", fallback=DEFAULT_PROMPT_SYS)

# f"Project structure:{structure}{PROMPT...}"
PROMPT_USER_STRUCTURE = config.get("api_requests", "prompt_user_structure",
                                   fallback=DEFAULT_PROMPT_USER_STRUCTURE)

# f"File name: {name}\n{content}\n{PROMPT...}{level}"
PROMPT_USER_FILE_ANALYZE = config.get("api_requests", "prompt_user_file_analyze",
                                      fallback=DEFAULT_PROMPT_USER_FILE_ANALYZE)

# f"{..SUMMARY_TASK}{summaries_text}{..SUMMARY_SOLUTIONS}\n{..SUMMARY_SKILLS}{..SUMMARY_RATING}{dev_level}"
PROMPT_USER_SUMMARY_TASK = config.get("api_requests", "prompt_user_summary_task",
                                      fallback=DEFAULT_PROMPT_USER_TASK)
PROMPT_USER_SUMMARY_SOLUTIONS = config.get("api_requests", "prompt_user_summary_solutions",
                                           fallback=DEFAULT_PROMPT_SOLUTIONS)
PROMPT_USER_SUMMARY_SKILLS = config.get("api_requests", "prompt_user_summary_skills",
                                        fallback=DEFAULT_PROMPT_SKILLS)
PROMPT_USER_SUMMARY_RATING = config.get("api_requests", "prompt_user_summary_rating",
                                        fallback=DEFAULT_PROMPT_RATING)

# f"{..REDUCE_TASK}{summaries_text}{..REDUCE_SOLUTIONS}\n{..REDUCE_SKILLS}{..REDUCE_RATING}{dev_level}"
PROMPT_USER_REDUCE_TASK = config.get("api_requests", "prompt_user_reduce_task",
                                     fallback=DEFAULT_PROMPT_USER_TASK)
PROMPT_USER_REDUCE_SOLUTIONS = config.get("api_requests", "prompt_user_reduce_solutions",
                                          fallback=DEFAULT_PROMPT_SOLUTIONS)
PROMPT_USER_REDUCE_SKILLS = config.get("api_requests", "prompt_user_reduce_skills",
                                       fallback=DEFAULT_PROMPT_SKILLS)
PROMPT_USER_REDUCE_RATING = config.get("api_requests", "prompt_user_reduce_rating",
                                       fallback=DEFAULT_PROMPT_RATING)
