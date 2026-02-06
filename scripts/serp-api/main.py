import logging
import sys
import os
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

from config import get_salesforce_client
from salesforce_client import SalesforceClient
from serp_client import SerpApiClient
from enrichment_service import EnrichmentService

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
    args = parser.parse_args()

    logger.info(f"Starting Enrichment... (Dry Run: {args.dry_run}, Limit: {args.limit})")

    # CSV output path (data/ at repo root, two levels up from scripts/serp-api/)
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    data_dir = str(data_dir)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = os.path.join(data_dir, f'enrichment_{timestamp}.csv')

    # Initialize services
    try:
        sf = get_salesforce_client()
        sf_client = SalesforceClient(sf)
        serp_client = SerpApiClient()
        service = EnrichmentService(sf_client, serp_client, csv_path)
        logger.info("Services initialized successfully.")
    except Exception as e:
        logger.error(f"Initialization Failed: {e}")
        return

    # Processing loop with seek pagination
    BATCH_SIZE = 1000
    MAX_WORKERS = 20

    total_processed = 0
    limit = args.limit
    last_id = None

    while True:
        try:
            fetch_limit = BATCH_SIZE
            if limit is not None:
                remaining = limit - total_processed
                if remaining <= 0:
                    break
                fetch_limit = min(BATCH_SIZE, remaining)

            accounts = sf_client.get_unenriched_accounts(limit=fetch_limit, after_id=last_id)
            if not accounts:
                logger.info("No more accounts to enrich.")
                break

            logger.info(f"Fetched {len(accounts)} accounts. Last ID: {accounts[-1]['Id']}")

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [
                    executor.submit(service.enrich_account, acc, args.dry_run)
                    for acc in accounts
                ]
                for future in as_completed(futures):
                    pass

            total_processed += len(accounts)
            last_id = accounts[-1]['Id']

            if len(accounts) < fetch_limit:
                break

        except Exception as e:
            logger.error(f"Critical Loop Error: {e}")
            break

    logger.info(f"Enrichment Finished. Processed {total_processed} accounts.")
    logger.info(f"Results logged to: {csv_path}")

if __name__ == "__main__":
    main()
