import logging
import csv
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

from config import get_salesforce_client
from salesforce_client import SalesforceClient
from serp_client import SerpApiClient
from supabase_client import get_db_client
from supabase_client import get_db_client
from enrichment_service import EnrichmentService
from sync_service import SyncService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Salesforce Enrichment Service")
    parser.add_argument("--dry-run", action="store_true", help="Run without modifying Salesforce")
    parser.add_argument("--limit", type=int, help="Limit the number of accounts to process", default=None)
    parser.add_argument("--sync-only", action="store_true", help="Run only the synchronization from Supabase to Salesforce")
    parser.add_argument("--sync", action="store_true", help="Run synchronization after enrichment")
    args = parser.parse_args()

    logger.info(f"Starting Enrichment... (Dry Run: {args.dry_run}, Limit: {args.limit})")

    # 1. Setup Resources
    # CSV logging has been removed in favor of Supabase only

    # 2. Initialize Service Stack
    try:
        # Salesforce
        sf = get_salesforce_client()
        sf_client = SalesforceClient(sf)
        
        # API & DB
        serp_client = SerpApiClient()
        db_client = get_db_client()
        
        # Service
        service = EnrichmentService(sf_client, serp_client, db_client)
        sync_service = SyncService(sf_client, db_client)
        logger.info("Services initialized successfully.")
    except Exception as e:
        logger.error(f"Initialization Failed: {e}")
        return

    # 4. Sync Only Mode
    if args.sync_only:
        sync_service.sync_pending_accounts(limit=args.limit if args.limit else 100, dry_run=args.dry_run)
        return

    # 3. Processing Loop
    BATCH_SIZE = 1000
    MAX_WORKERS = 20
    
    total_processed = 0
    limit = args.limit
    last_id = None

    while True:
        try:
            # Calculate fetch limit
            fetch_limit = BATCH_SIZE
            if limit is not None:
                remaining = limit - total_processed
                if remaining <= 0:
                    break
                fetch_limit = min(BATCH_SIZE, remaining)

            # Fetch Accounts
            accounts = sf_client.get_unenriched_accounts(limit=fetch_limit, after_id=last_id)
            if not accounts:
                logger.info("No more accounts to enrich.")
                break

            logger.info(f"Fetched {len(accounts)} accounts. Last ID: {accounts[-1]['Id']}")
            
            # Parallel Processing
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [
                    executor.submit(service.enrich_account, acc, args.dry_run) 
                    for acc in accounts
                ]
                # Wait for completion
                for future in as_completed(futures):
                    pass

            total_processed += len(accounts)
            last_id = accounts[-1]['Id']
            
            if len(accounts) < fetch_limit:
                break

        except Exception as e:
            logger.error(f"Critical Loop Error: {e}")
            break

    logger.info("Enrichment Finished.")

    # 5. Run Sync if requested
    if args.sync:
        sync_service.sync_pending_accounts(limit=args.limit if args.limit else 100, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
