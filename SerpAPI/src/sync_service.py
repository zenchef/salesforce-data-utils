import logging
import re
from typing import Dict, Any, Optional

from salesforce_client import SalesforceClient
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, sf_client: SalesforceClient, db_client: SupabaseClient):
        self.sf_client = sf_client
        self.db_client = db_client

    def sync_pending_accounts(self, limit: int = 100, dry_run: bool = False):
        """
        Fetches pending records from Supabase and updates Salesforce.
        """
        logger.info("Starting Sync Process...")
        
        # 1. Fetch pending records
        pending_records = self.db_client.get_unsynced_records(limit=limit)
        
        if not pending_records:
            logger.info("No pending records to sync.")
            return

        logger.info(f"Found {len(pending_records)} pending records.")

        success_count = 0
        failure_count = 0

        for record in pending_records:
            try:
                account_id = record.get('account_id')
                if not account_id:
                    continue

                # 2. Prepare Payload
                sf_payload = self._prepare_sf_payload(record)
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would update Account {account_id} with: {sf_payload}")
                    # Simulate success
                    self.db_client.update_sync_status(account_id, 'SYNCED')
                    success_count += 1
                    continue

                # 3. Update Salesforce
                if self.sf_client.update_account(account_id, sf_payload):
                    logger.info(f"Successfully synced Account {account_id}")
                    self.db_client.update_sync_status(account_id, 'SYNCED')
                    success_count += 1
                else:
                    logger.error(f"Failed to sync Account {account_id}")
                    self.db_client.update_sync_status(account_id, 'ERROR')
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"Error syncing record {record.get('account_id')}: {e}")
                self.db_client.update_sync_status(record.get('account_id'), 'ERROR')
                failure_count += 1
        
        logger.info(f"Sync Complete. Success: {success_count}, Failed: {failure_count}")

    def _prepare_sf_payload(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Supabase record fields to Salesforce Account fields.
        """
        return {
            "Google_Place_ID__c": record.get("google_place_id"),
            # "Google_Data_ID__c": record.get("google_data_id"), # Not in DB schema provided?
            "Google_Type__c": record.get("google_type__c"),
            "Google_Rating__c": record.get("google_rating__c"),
            "Google_Reviews__c": record.get("google_reviews__c"),
            "Google_Price__c": self._clean_price(record.get("google_price__c")),
            #"Google_Updated_Date__c": record.get("created_at"), # Maybe?
            "Prospection_Status__c": record.get("prospection_status__c"),
            "Has_Google_Accept_Bookings_Extension__c": record.get("has_google_accept_bookings_extension__c"),
            "HasGoogleDeliveryExtension__c": record.get("has_google_delivery_extension__c"),
            "HasGoogleTakeoutExtension__c": record.get("has_google_takeout_extension__c"),
            "Google_Thumbnail_URL__c": record.get("google_thumbnail_url__c"), # Check if in DB
            "Google_URL__c": record.get("google_url__c")
        }

    def _clean_price(self, price: Any) -> Any:
        """
        Clean price to match Salesforce Picklist ($, $$, $$$, $$$$).
        Logic copied from EnrichmentService to ensure consistency.
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
