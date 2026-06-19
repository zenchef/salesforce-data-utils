import os
from pathlib import Path
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Load .env from repo root (two levels up from scripts/chargebee-quote-automation/)
_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_root / '.env')

# Salesforce Credentials (shared with the rest of the repo)
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_TOKEN = os.getenv("SF_TOKEN")

# Path to the Firefox profile that is already logged in to Salesforce via SSO.
# Find it at about:profiles -> active profile -> "Root Directory".
FIREFOX_PROFILE_PATH = os.getenv("FIREFOX_PROFILE_PATH")


def get_salesforce_client() -> Salesforce:
    """Returns an authenticated Salesforce client using standard auth."""
    return Salesforce(
        username=SF_USERNAME,
        password=SF_PASSWORD,
        security_token=SF_TOKEN
    )


def validate_config():
    """Validates that necessary environment variables are set."""
    missing = []

    if not all([SF_USERNAME, SF_PASSWORD, SF_TOKEN]):
        missing.append("Salesforce Credentials (SF_USERNAME, SF_PASSWORD, SF_TOKEN)")

    if not FIREFOX_PROFILE_PATH:
        missing.append("FIREFOX_PROFILE_PATH")

    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")


# Validate on import
validate_config()
