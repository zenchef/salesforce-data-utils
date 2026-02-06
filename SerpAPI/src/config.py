import os
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Salesforce Credentials
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_TOKEN = os.getenv("SF_TOKEN")

# SERP API Key
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

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

    if not SERPAPI_KEY:
        missing.append("SERPAPI_KEY")

    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")

# Validate on import
validate_config()
