import re
import logging
import time
from typing import Dict, Any, Optional
from fuzzywuzzy import fuzz

from salesforce_client import SalesforceClient
from serp_client import SerpApiClient
from supabase_client import SupabaseClient, get_db_client

logger = logging.getLogger(__name__)

class EnrichmentService:
    def __init__(self, sf_client: SalesforceClient, serp_client: SerpApiClient, db_client: SupabaseClient):
        self.sf_client = sf_client
        self.serp_client = serp_client
        self.db_client = db_client

    def enrich_account(self, account: Dict[str, Any], dry_run: bool):
        """
        Orchestrates the enrichment flow for a single account.
        1. Clean Data & Construct Query
        2. Search SerpApi
        3. Match Validation (Sanity Check)
        4. Log Result (Supabase only)
        """
        aid = account['Id']
        try:
            # 0. Check Pre-existence to Save API Costs
            if self.db_client.record_exists(aid):
                logger.info(f"Account {aid} already enriched (Skipping SerpAPI)")
                return

            # 1. Search Construction
            search_query = self._construct_search_query(account)
            if not search_query:
                self._log_result(aid, 'SKIPPED', 'Insufficient data', None)
                return

            logger.info(f"Searching for: {search_query}")
            result_data = self.serp_client.search_google_maps(search_query)

            if not result_data:
                logger.info(f"No results found for Account {aid}")
                self._log_result(aid, 'NO_RESULT', 'No SERP results found', None)
                return

            # 2. Sanity Check
            # Rule: Title must match either Name OR Nom_du_restaurant__c >= 80%
            sf_name = account.get('Name') or ""
            sf_restaurant_name = account.get('Nom_du_restaurant__c') or ""
            google_title = result_data.get('Title') or ""
            
            # Calculate fuzzy match scores for both fields
            name_score = fuzz.token_sort_ratio(sf_name, google_title)
            restaurant_name_score = fuzz.token_sort_ratio(sf_restaurant_name, google_title)
            
            # Use the higher score
            match_score = max(name_score, restaurant_name_score)
            matched_field = 'Name' if name_score >= restaurant_name_score else 'Nom_du_restaurant__c'
            
            if match_score < 80:
                logger.warning(
                    f"Sanity Check Failed for {aid}. "
                    f"Name score: {name_score}%, Nom_du_restaurant score: {restaurant_name_score}%"
                )
                self._log_result(
                    aid, 'SKIPPED_SANITY_CHECK', 
                    f"Best match: {match_score}% < 80%", 
                    result_data
                )
                return
            
            logger.info(
                f"Sanity Check Passed for {aid}. "
                f"Matched on {matched_field}: {match_score}%"
            )

            # 3. Log Success (Supabase Only)
            # Salesforce update logic has been removed.
            logger.info(f"Enriched Account {aid} - Logging to Supabase")
            self._log_result(aid, 'ENRICHED', 'Enrichment successful', result_data)

        except Exception as e:
            logger.error(f"Error processing account {aid}: {e}")
            self._log_result(aid, 'ERROR', str(e), None)

    def _construct_search_query(self, account: Dict[str, Any]) -> str:
        parts = [
            account.get('Name'),
            account.get('BillingStreet'),
            account.get('BillingCity'),
            account.get('BillingCountry'),
            "Restaurant" # Rule: Append Restaurant
        ]
        return " ".join([p for p in parts if p]).strip()

    def _prepare_update_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data to update in Salesforce Account.
        Note: Title and Address are NOT Account fields - they're only used for logging to CSV/Supabase.
        """
        return {
            "Google_Place_ID__c": result.get("Google_Place_ID__c"),
            "Google_Data_ID__c": result.get("Google_Data_ID__c"),
            "Google_Type__c": result.get("Google_Type__c"),
            "Google_Rating__c": result.get("Google_Rating__c"),
            "Google_Reviews__c": result.get("Google_Reviews__c"),
            "Google_Price__c": self._clean_price(result.get("Google_Price__c")),
            "Google_Updated_Date__c": result.get("Google_Updated_Date__c"),
            "Prospection_Status__c": result.get("Prospection_Status__c"),
            "Has_Google_Accept_Bookings_Extension__c": result.get("Has_Google_Accept_Bookings_Extension__c"),
            "HasGoogleDeliveryExtension__c": result.get("HasGoogleDeliveryExtension__c"),
            "HasGoogleTakeoutExtension__c": result.get("HasGoogleTakeoutExtension__c"),
            "Google_Thumbnail_URL__c": result.get("Google_Thumbnail_URL__c"),
            "Google_URL__c": result.get("Google_URL__c")
        }

    def _clean_price(self, price: Any) -> Any:
        """
        Clean price to match Salesforce Picklist ($, $$, $$$, $$$$).
        Handles:
        - Integers 1-4: Direct mapping ($ - $$$$)
        - Values < 5: Treated as levels
        - Values >= 5: Treated as Raw Amount
            < 20: $
            20-29: $$
            30-49: $$$
            >= 50: $$$$
        - Strings like "€20–30" -> Extracts range (20, 30) -> Average 25 -> $$
        """
        if not price:
            return None
        
        val = None

        # 1. Try to extract a numeric value or range
        if isinstance(price, (int, float)):
             val = float(price)
        elif isinstance(price, str):
            # First, check for a range like "20-30" or "20–30" (supports hyphen and en-dash)
            # We look for two numbers separated by a dash/en-dash, possibly with spaces.
            range_match = re.search(r'(\d+)\s*[–-]\s*(\d+)', price)
            
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                val = (low + high) / 2
            else:
                # Fallback to single number extraction
                match = re.search(r'\d+', price)
                if match:
                    val = float(match.group())
            
            # If we couldn't parse a number/range, check for standard count of $
            if val is None:
                count = price.count('$')
                # Only use count if it's within standard range 1-4
                if 1 <= count <= 4:
                    return "$" * count
                    
        # 2. Key Logic: Map Value to Level
        if val is not None:
             # Ensure val is treated as float for comparison
             v = float(val)
             
             if 1 <= v <= 4:
                 # It's already a level (1, 2, 3, 4).
                 # Note: If average turned out to be small (e.g. range 2-4 -> avg 3), this treats it as level. 
                 # This is ambiguous (is it €3 or Level 3?), but consistent with previous logic.
                 return "$" * int(v)
             elif v < 20:
                 return "$"
             elif 20 <= v < 30:
                 return "$$"
             elif 30 <= v < 50:
                 return "$$$"
             else: # >= 50
                 return "$$$$"

        return None

    def _log_result(self, aid: str, status: str, message: str, result_data: Optional[Dict]):
        # Supabase Write with lowercase keys (PostgreSQL convention)
        try:
            supabase_entry = {
                'account_id': aid,
                'status': status,
                'message': message,
                'google_place_id': result_data.get('Google_Place_ID__c') if result_data else None,
                'title': result_data.get('Title') if result_data else None,
                'address': result_data.get('Address') if result_data else None,
                'google_type__c': result_data.get('Google_Type__c') if result_data else None,
                'google_rating__c': result_data.get('Google_Rating__c') if result_data else None,
                'google_reviews__c': result_data.get('Google_Reviews__c') if result_data else None,
                'google_price__c': result_data.get('Google_Price__c') if result_data else None,
                'has_google_accept_bookings_extension__c': result_data.get('Has_Google_Accept_Bookings_Extension__c') if result_data else None,
                'has_google_delivery_extension__c': result_data.get('HasGoogleDeliveryExtension__c') if result_data else None,
                'has_google_takeout_extension__c': result_data.get('HasGoogleTakeoutExtension__c') if result_data else None,
                'prospection_status__c': result_data.get('Prospection_Status__c') if result_data else None,
                'google_url__c': result_data.get('Google_URL__c') if result_data else None,
                'sync_status': 'PENDING'
            }
            # 1. Update/Insert in Main Table (Current State)
            self.db_client.insert_record(supabase_entry)
            
            # 2. Insert into History Table (Audit Log / Backup)
            self.db_client.insert_history_record(supabase_entry)
            
        except Exception as e:
            logger.error(f"Error logging result: {e}")
            # Don't throw, let the process continue
