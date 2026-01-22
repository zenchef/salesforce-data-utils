import os
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Salesforce Credentials
SF_DOMAIN = os.getenv("DOMAIN")
SF_CONSUMER_KEY = os.getenv("CONSUMER_KEY")
SF_CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
SF_USERNAME = os.getenv("USERNAME")
SF_PASSWORD = os.getenv("PASSWORD")
SF_SECURITY_TOKEN = os.getenv("SECURITY_TOKEN")

# SERP API Key
SERPAPI_KEY = os.getenv("SERPAPI_KEY") or os.getenv("SEPRAPI_KEY")

# Supabase Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_salesforce_client() -> Salesforce:
    """
    Returns an authenticated Salesforce client.
    
    Priority of Auth Methods:
    1. Connected App (Username, Password, Consumer Key, Consumer Secret, [Security Token])
       - This is the preferred method if Key/Secret are provided.
    2. Standard (Username, Password, Security Token)
       - Used if Consumer Key/Secret are missing.
       
    The 'domain' argument (SF_DOMAIN) is passed to handle 'test' (Sandbox) or specific MyDomain instances.
    """
    
    # Common arguments
    auth_args = {
        'username': SF_USERNAME,
        'password': SF_PASSWORD,
        'security_token': SF_SECURITY_TOKEN,
        'domain': SF_DOMAIN
    }

    # Filter out None values
    auth_args = {k: v for k, v in auth_args.items() if v is not None}

    if SF_CONSUMER_KEY and SF_CONSUMER_SECRET:
        # Connected App Auth Flow
        auth_args['consumer_key'] = SF_CONSUMER_KEY
        auth_args['consumer_secret'] = SF_CONSUMER_SECRET
    
    return Salesforce(**auth_args)

def validate_config():
    """Validates that necessary environment variables are set."""
    missing = []
    
    # Check essential Salesforce credentials (at least one auth method)
    # Method 1: Connected App
    has_connected_app = all([SF_USERNAME, SF_PASSWORD, SF_CONSUMER_KEY, SF_CONSUMER_SECRET])
    # Method 2: Standard
    has_standard = all([SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN])
    # Method 3: Client Credentials / User-specified flow (Key + Secret + Domain)
    has_client_creds = all([SF_CONSUMER_KEY, SF_CONSUMER_SECRET, SF_DOMAIN])

    if not (has_connected_app or has_standard or has_client_creds):
        missing.append("Salesforce Credentials. Needs one of: \n"
                       "1. Connected App (User+Pass+Key+Secret)\n"
                       "2. Standard (User+Pass+Token)\n"
                       "3. Client Credentials/Domain (Key+Secret+Domain)")

    if not SERPAPI_KEY:
        missing.append("SERPAPI_KEY")

    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")

    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")

# Validate on import
validate_config()
