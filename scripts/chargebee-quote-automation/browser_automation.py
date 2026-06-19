import logging
from typing import Any, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# Default time (seconds) to wait for a clickable element before giving up.
DEFAULT_WAIT = 20


class QuoteBrowserAutomation:
    """Drives Firefox (Salesforce Classic) to run quote actions via UI clicks.

    Relies on a Firefox profile that is already logged in to Salesforce through
    SSO, so no credentials are entered here. Salesforce must be in Classic mode;
    the targeted buttons do not exist in Lightning Experience.
    """

    def __init__(self, instance_url: str, firefox_profile_path: str, wait: int = DEFAULT_WAIT):
        self.instance_url = instance_url.rstrip("/")
        self.wait = wait

        options = webdriver.FirefoxOptions()
        options.add_argument("-profile")
        options.add_argument(firefox_profile_path)
        self.driver = webdriver.Firefox(options=options)

    def _record_url(self, record_id: str) -> str:
        return f"{self.instance_url}/{record_id}"

    def open_record(self, record_id: str):
        self.driver.get(self._record_url(record_id))

    def dismiss_first_visit_prompt(self):
        """Click the Classic landing/confirmation button shown on first navigation."""
        self.driver.find_element(
            By.CLASS_NAME, "button.button.mb12.secondary.wide"
        ).click()

    def click_generate_pdf(self):
        generate_pdf_button = WebDriverWait(self.driver, self.wait).until(
            EC.element_to_be_clickable((By.NAME, "chargebeeapps__generate_quote_pdf"))
        )
        generate_pdf_button.click()

        confirm_button = WebDriverWait(self.driver, self.wait).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "slds-button.slds-button_brand"))
        )
        confirm_button.click()

    def click_sync_to_opportunity(self):
        sync_button = WebDriverWait(self.driver, self.wait).until(
            EC.element_to_be_clickable((By.NAME, "chargebeeapps__sync_to_opportunity"))
        )
        sync_button.click()

        confirm_sync_button = WebDriverWait(self.driver, self.wait).until(
            EC.element_to_be_clickable((By.NAME, "j_id0:theform:SyncToOpportunityBtn"))
        )
        confirm_sync_button.click()

    def run_actions(self, record: Dict[str, Any]):
        """Generate the quote PDF, then sync the quote to its opportunity."""
        record_id = record["Id"]
        self.open_record(record_id)
        self.click_generate_pdf()
        self.open_record(record_id)
        self.click_sync_to_opportunity()

    def run_actions_optimized(self, record: Dict[str, Any]):
        """Only run the actions that have not already completed for this record.

        Slower per record than run_actions() because it inspects state, but it
        avoids redoing work when re-running over a partially processed batch.
        """
        record_id = record["Id"]
        opportunity = record.get("chargebeeapps__Opportunity__r") or {}

        if record.get("chargebeeapps__CB_Acceptance_Link__c") is None:
            self.open_record(record_id)
            self.click_generate_pdf()

        if opportunity.get("Count_Opportunity_Products__c") == 0:
            self.open_record(record_id)
            self.click_sync_to_opportunity()

    def quit(self):
        self.driver.quit()
