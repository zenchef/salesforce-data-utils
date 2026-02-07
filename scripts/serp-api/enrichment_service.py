import re
import csv
import os
import logging
import threading
import datetime
from collections import Counter
from typing import Dict, Any, Optional, Set

from fuzzywuzzy import fuzz

from salesforce_client import SalesforceClient
from serp_client import SerpApiClient

# Custom SUCCESS log level (between INFO and WARNING)
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

logger = logging.getLogger(__name__)


class EnrichmentService:
    PROCESSED_CSV = 'processed_accounts.csv'
    PROCESSED_HEADERS = ['account_id', 'status', 'timestamp']

    def __init__(self, sf_client: SalesforceClient, serp_client: SerpApiClient, csv_path: str, data_dir: str):
        self.sf_client = sf_client
        self.serp_client = serp_client
        self.csv_path = csv_path
        self.data_dir = data_dir
        self._csv_lock = threading.Lock()
        self._processed_lock = threading.Lock()
        self._processed_path = os.path.join(data_dir, self.PROCESSED_CSV)
        self.excluded_ids = self._load_processed_ids()
        self._stats_lock = threading.Lock()
        self._stats = Counter()
        self._init_csv()

    def get_stats(self) -> Counter:
        """Return a copy of the run stats."""
        return Counter(self._stats)

    def _count(self, status: str):
        """Thread-safe stats increment."""
        with self._stats_lock:
            self._stats[status] += 1

    def _load_processed_ids(self) -> Set[str]:
        """Load already-processed account IDs from the persistent CSV."""
        ids = set()
        if not os.path.exists(self._processed_path):
            return ids
        with open(self._processed_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row['account_id'])
        logger.info(f"Loaded {len(ids)} already-processed account IDs to exclude.")
        return ids

    def _mark_processed(self, account_id: str, status: str):
        """Append an account to the persistent processed CSV (thread-safe)."""
        with self._processed_lock:
            file_exists = os.path.exists(self._processed_path)
            with open(self._processed_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(self.PROCESSED_HEADERS)
                writer.writerow([account_id, status, datetime.datetime.now().isoformat()])

    def _init_csv(self):
        """Create CSV with headers only if the file doesn't already exist."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'account_id', 'account_name', 'status', 'message',
                    'google_place_id', 'google_title', 'google_address',
                    'google_type', 'google_rating', 'google_reviews',
                    'google_price', 'google_url', 'match_score', 'matched_field',
                    'timestamp'
                ])

    def _write_csv_row(self, row: list):
        """Thread-safe CSV write."""
        with self._csv_lock:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)

    def enrich_account(self, account: Dict[str, Any], dry_run: bool):
        """
        Enrichment flow for a single account:
        1. Construct search query
        2. Search SerpApi
        3. Validate match (fuzzy >= 80%)
        4. Update Salesforce (unless dry-run)
        5. Log to CSV
        """
        aid = account['Id']
        account_name = account.get('Name', '')

        # Skip if already processed in a previous run
        if aid in self.excluded_ids:
            logger.debug(f"Skipping already-processed account {aid}")
            self._count('ALREADY_PROCESSED')
            return

        try:
            # 1. Build search query
            search_query = self._construct_search_query(account)
            if not search_query:
                self._log_csv(aid, account_name, 'SKIPPED', 'Insufficient data', None, 0, '')
                self._mark_processed(aid, 'SKIPPED')
                self._count('SKIPPED')
                return

            logger.info(f"Searching for: {search_query}")
            result_data = self.serp_client.search_google_maps(search_query)

            if not result_data:
                logger.info(f"No results found for Account {aid}")
                self._log_csv(aid, account_name, 'NO_RESULT', 'No SERP results found', None, 0, '')
                self._mark_processed(aid, 'NO_RESULT')
                self._count('NO_RESULT')
                return

            # 2. Sanity Check - fuzzy match >= 80%
            sf_name = account.get('Name') or ""
            sf_restaurant_name = account.get('Nom_du_restaurant__c') or ""
            google_title = result_data.get('Title') or ""

            name_score = fuzz.token_sort_ratio(sf_name, google_title)
            restaurant_name_score = fuzz.token_sort_ratio(sf_restaurant_name, google_title)

            match_score = max(name_score, restaurant_name_score)
            matched_field = 'Name' if name_score >= restaurant_name_score else 'Nom_du_restaurant__c'

            if match_score < 80:
                logger.warning(
                    f"Sanity Check Failed for {aid}. "
                    f"Name score: {name_score}%, Nom_du_restaurant score: {restaurant_name_score}%"
                )
                self._log_csv(aid, account_name, 'SKIPPED_SANITY_CHECK',
                              f"Best match: {match_score}% < 80%", result_data, match_score, matched_field)
                self._mark_processed(aid, 'SKIPPED_SANITY_CHECK')
                self._count('SKIPPED_SANITY_CHECK')
                return

            logger.info(f"Sanity Check Passed for {aid}. Matched on {matched_field}: {match_score}%")

            # 3. Update Salesforce
            payload = self._prepare_update_payload(result_data)

            if dry_run:
                logger.info(f"[DRY RUN] Would update Account {aid} with: {payload}")
            else:
                if self.sf_client.update_account(aid, payload):
                    logger.log(SUCCESS, f"Updated Account {aid} in Salesforce")
                else:
                    logger.error(f"Failed to update Account {aid}")
                    self._log_csv(aid, account_name, 'ERROR', 'Salesforce update failed',
                                  result_data, match_score, matched_field)
                    return

            # 4. Log success to CSV
            status = 'ENRICHED (DRY RUN)' if dry_run else 'ENRICHED'
            self._log_csv(aid, account_name, status, 'OK', result_data, match_score, matched_field)
            self._count(status)

        except Exception as e:
            logger.error(f"Error processing account {aid}: {e}")
            self._log_csv(aid, account_name, 'ERROR', str(e), None, 0, '')
            self._count('ERROR')

    def _construct_search_query(self, account: Dict[str, Any]) -> str:
        parts = [
            account.get('Name'),
            account.get('BillingStreet'),
            account.get('BillingCity'),
            account.get('BillingCountry'),
            "Restaurant"
        ]
        return " ".join([p for p in parts if p]).strip()

    def _prepare_update_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Map serp result to Salesforce Account fields."""
        payload = {
            "Google_Place_ID__c": result.get("Google_Place_ID__c"),
            "Google_Data_ID__c": result.get("Google_Data_ID__c"),
            "Google_Type__c": result.get("Google_Type__c"),
            "Google_Rating__c": result.get("Google_Rating__c"),
            "Google_Reviews__c": result.get("Google_Reviews__c"),
            "Google_Price__c": self._clean_price(result.get("Google_Price__c")),
            "Google_Updated_Date__c": result.get("Google_Updated_Date__c"),
            "HasGoogleAcceptBookingsExtension__c": result.get("HasGoogleAcceptBookingsExtension__c"),
            "HasGoogleDeliveryExtension__c": result.get("HasGoogleDeliveryExtension__c"),
            "HasGoogleTakeoutExtension__c": result.get("HasGoogleTakeoutExtension__c"),
            "Google_Thumbnail_URL__c": result.get("Google_Thumbnail_URL__c"),
            "Google_URL__c": result.get("Google_URL__c"),
        }
        # Add closure status if detected
        if result.get("Prospection_Status__c"):
            payload["Prospection_Status__c"] = result["Prospection_Status__c"]

        # Truncate URL fields to 255 chars (Salesforce field limit)
        for url_field in ('Google_Thumbnail_URL__c', 'Google_URL__c'):
            if payload.get(url_field) and len(payload[url_field]) > 255:
                payload[url_field] = payload[url_field][:255]

        # Remove None values to avoid overwriting existing SF data with blanks
        return {k: v for k, v in payload.items() if v is not None}

    def _clean_price(self, price: Any) -> Any:
        """
        Clean price to match Salesforce Picklist ($, $$, $$$, $$$$).
        Handles integers, euro ranges like "€20–30", and $ strings.
        """
        if not price:
            return None

        val = None

        if isinstance(price, (int, float)):
            val = float(price)
        elif isinstance(price, str):
            range_match = re.search(r'(\d+)\s*[–-]\s*(\d+)', price)
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                val = (low + high) / 2
            else:
                match = re.search(r'\d+', price)
                if match:
                    val = float(match.group())

            if val is None:
                count = price.count('$')
                if 1 <= count <= 4:
                    return "$" * count

        if val is not None:
            v = float(val)
            if 1 <= v <= 4:
                return "$" * int(v)
            elif v < 20:
                return "$"
            elif 20 <= v < 30:
                return "$$"
            elif 30 <= v < 50:
                return "$$$"
            else:
                return "$$$$"

        return None

    def _log_csv(self, aid: str, account_name: str, status: str, message: str,
                 result_data: Optional[Dict], match_score: int, matched_field: str):
        """Write a row to the CSV log."""
        self._write_csv_row([
            aid,
            account_name,
            status,
            message,
            result_data.get('Google_Place_ID__c') if result_data else '',
            result_data.get('Title') if result_data else '',
            result_data.get('Address') if result_data else '',
            result_data.get('Google_Type__c') if result_data else '',
            result_data.get('Google_Rating__c') if result_data else '',
            result_data.get('Google_Reviews__c') if result_data else '',
            result_data.get('Google_Price__c') if result_data else '',
            result_data.get('Google_URL__c') if result_data else '',
            match_score,
            matched_field,
            datetime.datetime.now().isoformat()
        ])
