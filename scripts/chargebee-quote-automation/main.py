import argparse
import logging
import sys

import pandas as pd

from config import FIREFOX_PROFILE_PATH, get_salesforce_client
from salesforce_client import QuoteSalesforceClient
from browser_automation import QuoteBrowserAutomation

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def resolve_filter_field(sample_id: str) -> str:
    """Chargebee quote names start with 'ZCQUO-'; everything else is a record Id."""
    return "Name" if "ZCQUO-" in str(sample_id) else "Id"


def main():
    parser = argparse.ArgumentParser(
        description="Generate quote PDFs and sync quotes to opportunities via the Salesforce Classic UI."
    )
    parser.add_argument("--csv", required=True, help="Path to the CSV file containing quote identifiers")
    parser.add_argument("--id-column", default="Name", help="CSV column holding the quote Name or Id (default: Name)")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Row index to resume from after a failure (default: 0)")
    parser.add_argument("--optimized", action="store_true",
                        help="Skip actions already completed for a record (use when re-running a batch)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    if args.id_column not in df.columns:
        logger.error(f"Column '{args.id_column}' not found in {args.csv}. Available: {list(df.columns)}")
        return

    quote_ids = df[args.id_column].tolist()
    if not quote_ids:
        logger.info("No quote identifiers found in the CSV.")
        return

    filter_field = resolve_filter_field(quote_ids[0])
    logger.info(f"Processing {len(quote_ids)} quotes by '{filter_field}' (optimized: {args.optimized}).")

    sf = get_salesforce_client()
    sf_client = QuoteSalesforceClient(sf)
    browser = QuoteBrowserAutomation(sf_client.instance_url, FIREFOX_PROFILE_PATH)

    try:
        for i, quote_id in enumerate(quote_ids):
            if i < args.start_from:
                continue

            logger.info(f"=== RECORD {i}: {quote_id}")

            record = sf_client.get_quote_record(quote_id, filter_field)
            if not record:
                logger.warning(f"No quote found for {quote_id}; skipping.")
                continue

            # On the very first navigation, dismiss the Classic landing prompt.
            browser.open_record(record["Id"])
            if i == args.start_from:
                browser.dismiss_first_visit_prompt()

            if args.optimized:
                browser.run_actions_optimized(record)
            else:
                browser.run_actions(record)

        logger.info("Finished processing all quotes.")
    except Exception as e:
        logger.error(f"Run stopped at an error: {e}")
        logger.error("Re-run with --start-from <last successful record index> to resume.")
        raise
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
