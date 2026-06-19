import logging
from typing import Any, Dict, Optional
from simple_salesforce import Salesforce
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class QuoteSalesforceClient:
    """Read-only Salesforce client used to resolve Chargebee quote records.

    The browser automation only needs each quote's record Id (to navigate to it)
    plus a couple of fields used to decide whether an action still needs to run.
    """

    def __init__(self, sf: Salesforce):
        self.sf = sf

    @property
    def instance_url(self) -> str:
        """Base instance URL, e.g. https://zenchef.my.salesforce.com."""
        return f"https://{self.sf.sf_instance}"

    def get_quote_record(self, quote_id: str, filter_field: str) -> Optional[Dict[str, Any]]:
        """Fetch a single Chargebee quote record by Name or Id.

        Returns the record dict (or None if not found). Fields mirror the
        original automation so the optimized re-run logic keeps working.
        """
        soql = (
            "SELECT "
            "Id, "
            "chargebeeapps__CB_Acceptance_Link__c, "
            "chargebeeapps__Opportunity__r.chargebeeapps__Payment_Link__c, "
            "chargebeeapps__Opportunity__r.Count_Opportunity_Products__c "
            "FROM chargebeeapps__CB_Quote__c "
            f"WHERE {filter_field} = '{quote_id}'"
        )

        try:
            results = self.sf.query(soql)
            records = results.get("records", [])
            return records[0] if records else None
        except RequestException as e:
            logger.error(f"Error fetching quote {quote_id}: {e}")
            return None
