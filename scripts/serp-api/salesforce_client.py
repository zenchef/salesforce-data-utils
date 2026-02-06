import logging
from typing import List, Dict, Any, Optional
from simple_salesforce import Salesforce
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SalesforceClient:
    def __init__(self, sf: Salesforce):
        self.sf = sf

    def merge_accounts(self, master_id: str, duplicate_ids: List[str]) -> bool:
        """
        Merge duplicate accounts into a master account using the Salesforce Merge API.
        This automatically re-parents related records and deletes the duplicates.
        """
        if not duplicate_ids:
            return True
            
        url = f"{self.sf.base_url}sobjects/Account/{master_id}/merge"
        payload = {
            "idsToMerge": duplicate_ids
        }
        
        try:
            # We use the lower-level request method to hit the specific merge endpoint
            self.sf.session.request("POST", url, json=payload, headers=self.sf.headers)
            logger.info(f"Successfully merged {duplicate_ids} into {master_id}")
            return True
        except RequestException as e:
            logger.error(f"Error merging accounts into {master_id}: {e}")
            return False


    def get_unenriched_accounts(self, limit: int = 100, after_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch accounts where Google_Place_ID__c is null.
        Excludes accounts with RecordType = 'Parent'.
        Supports 'seek pagination' via after_id.
        """
        clause = ""
        if after_id:
            clause = f"AND Id > '{after_id}'"
            
        query = (
            "SELECT Id, Name, Nom_du_restaurant__c, BillingStreet, BillingCity, BillingCountry, "
            "Website, Phone, Type, IsCustomer__c, RecordType.Name "
            "FROM Account "
            "WHERE Google_Place_ID__c = null AND Hotel_Restaurant__c = false AND RecordType.Name != 'Parent' "
            f"{clause} "
            "ORDER BY Id ASC "
            "LIMIT {}"
        ).format(limit)
        
        try:
            results = self.sf.query_all(query)
            return results['records']
        except RequestException as e:
            logger.error(f"Error fetching accounts: {e}")
            return []

    def update_account(self, account_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a specific account with new data.
        """
        try:
            self.sf.Account.update(account_id, data)
            logger.info(f"Successfully updated Account {account_id}")
            return True
        except RequestException as e:
            logger.error(f"Error updating account {account_id}: {e}")
            return False

    def get_potential_duplicates(self, google_place_id: str) -> List[Dict[str, Any]]:
        """
        Find accounts with the same Google Place ID.
        """
        query = (
            "SELECT Id, Name, Google_Place_ID__c, LastActivityDate, Type "
            "FROM Account "
            "WHERE Google_Place_ID__c = '{}'"
        ).format(google_place_id)
        
        try:
            results = self.sf.query(query)
            return results['records']
        except RequestException as e:
            logger.error(f"Error checking duplicates for {google_place_id}: {e}")
            return []

    def count_unenriched_accounts(self) -> int:
        """
        Count total accounts needing enrichment.
        """
        query = "SELECT COUNT() FROM Account WHERE Google_Place_ID__c = null AND Hotel_Restaurant__c = false"
        try:
            results = self.sf.query(query)
            return results['totalSize']
        except RequestException as e:
            logger.error(f"Error counting accounts: {e}")
            return 0
