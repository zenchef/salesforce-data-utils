import logging
import datetime
from typing import Dict, Any, Optional
from serpapi import GoogleSearch

from config import SERPAPI_KEY

logger = logging.getLogger(__name__)

class SerpApiClient:
    def __init__(self, api_key: str = SERPAPI_KEY):
        self.api_key = api_key
        if not self.api_key:
            logger.warning("SERPAPI_KEY is not set. API calls will fail.")

    def search_google_maps(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search Google Maps for a given query (Name + Address + City).
        Returns the data dictionary for the *first* (best) local result.
        """
        params = {
            "engine": "google_maps",
            "q": query,
            "api_key": self.api_key,
            "type": "search",
            "hl": "en", # Force English for consistent parsing of fields likes 'Open' or 'Closed'
            "gl": "us"  # Defaulting to US or making it optional could be better, but 'us' is a safe default for global coverage usually
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for error in response
            if "error" in results:
                logger.error(f"SERP API Error: {results['error']}")
                return None
            
            # We usually look at 'local_results' or 'place_results' depending on query specificity
            # For a general search, we might get a list 'local_results'
            local_results = results.get("local_results", [])
            
            if not local_results:
                # Sometimes if it's a direct match it might be in 'place_results'
                if "place_results" in results:
                    return self._process_result(results["place_results"])
                
                logger.info(f"No results found for query: {query}")
                return None
            
            # Return the first result detailed info
            return self._process_result(local_results[0])

        except Exception as e:
            logger.error(f"Exception during SERP API call: {e}")
            return None

    def _process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map SERP API result to our Salesforce Schema structure.
        """
        
        # Extract fields
        # Convert type array to string for Salesforce
        restaurant_type = result.get("type")
        if isinstance(restaurant_type, list):
            restaurant_type = ", ".join(restaurant_type)
        
        mapped = {
            "Google_Place_ID__c": result.get("place_id"),
            "Google_Data_ID__c": result.get("data_id"),
            "Google_Type__c": restaurant_type, # e.g. "French restaurant, Bistro"
            "Google_Rating__c": result.get("rating"),
            "Google_Reviews__c": result.get("reviews"),
            "Google_Price__c": result.get("price"), # e.g. "$$"
            "Google_Updated_Date__c": datetime.date.today().isoformat(),
            "Title": result.get("title"), 
            "Address": result.get("address"),
            "Prospection_Status__c": None, 
            "HasGoogleAcceptBookingsExtension__c": False,
            "HasGoogleDeliveryExtension__c": False,
            "HasGoogleTakeoutExtension__c": False,
            "Google_Thumbnail_URL__c": result.get("thumbnail"),
            "Google_URL__c": result.get("website") # Mapping SERP website to Google_URL__c as a safe storage
        }
        
        # Check extensions/bookings
        # 1. Check 'reserve_a_table' link presence
        if result.get("reserve_a_table"):
             mapped["HasGoogleAcceptBookingsExtension__c"] = True
        
        # 2. Check 'extensions' list (older format or specific ad extensions)
        extensions = result.get("extensions", [])
        if extensions:
             for ext in extensions:
                 if "booking" in str(ext).lower() or "reserve" in str(ext).lower():
                      mapped["HasGoogleAcceptBookingsExtension__c"] = True

        # 3. Check Service Options (Delivery / Takeout)
        service_options = result.get("service_options", {})
        # service_options is often a dict like {"dine_in": True, "delivery": True} or list
        if isinstance(service_options, dict):
            mapped["HasGoogleDeliveryExtension__c"] = service_options.get("delivery", False)
            mapped["HasGoogleTakeoutExtension__c"] = service_options.get("takeout", False)
        elif isinstance(service_options, list):
             # sometimes it's a list of strings ["Dine-in", "Takeout", "Delivery"]
             options_str = [str(o).lower() for o in service_options]
             mapped["HasGoogleDeliveryExtension__c"] = "delivery" in options_str
             mapped["HasGoogleTakeoutExtension__c"] = "takeout" in options_str or "pickup" in options_str

        # Check for closure status
        operating_status = result.get("operating_status")
        if operating_status == "PERMANENTLY_CLOSED":
            mapped["Prospection_Status__c"] = "Permanently Closed"
        elif operating_status == "TEMPORARILY_CLOSED":
            mapped["Prospection_Status__c"] = "Temporarily Closed"
            
        return mapped
