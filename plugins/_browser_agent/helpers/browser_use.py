import importlib

from helpers import dotenv

dotenv.save_dotenv_value("ANONYMIZED_TELEMETRY", "false")

browser_use = importlib.import_module("browser_use")
