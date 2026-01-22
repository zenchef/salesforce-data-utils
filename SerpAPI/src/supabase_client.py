from supabase import create_client, Client
import logging
from typing import Dict, Any, List, Optional

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be set in environment variables.")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.table_name = "enrichment_results"
        self.history_table_name = "enrichment_history"

    def record_exists(self, account_id: str) -> bool:
        """
        Check if a record already exists for the given Account_ID.
        Returns True if exists, False otherwise.
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("account_id")\
                .eq("account_id", account_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error checking if record exists: {e}")
            return False

    def get_existing_record(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the existing record for an Account_ID if it exists.
        Returns the record dict or None if not found.
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("account_id", account_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving existing record: {e}")
            return None

    def insert_record(self, record: Dict[str, Any]) -> Optional[Any]:
        """
        Inserts or updates a record in Supabase using upsert.
        Uses Account_ID as unique key to prevent duplicates.
        Checks database first to avoid duplicate attempts.
        SAFE: Catches exceptions preventing crash, logs error.
        """
        try:
            # Create a copy to avoid mutating the original record
            payload = record.copy()
            account_id = payload.get('account_id')
            
            # Remove Timestamp if present (though it shouldn't be in supabase payload)
            if 'timestamp' in payload:
                del payload['timestamp']
            
            # Check if record already exists
            existing_record = self.get_existing_record(account_id) if account_id else None
            
            if existing_record:
                # Compare payload with existing record
                # We only check keys present in the new payload
                has_changes = False
                for key, new_value in payload.items():
                    # Skip if key not in existing (shouldn't happen with fixed schema but good for safety)
                    if key not in existing_record:
                        continue
                    
                    old_value = existing_record.get(key)
                    # Simple equality check
                    # Note: You might need specific handling for None vs "" if that matters to you
                    if str(new_value) != str(old_value) and new_value is not None:
                         # Double check for None vs None equality via str() might be tricky
                         # Better: direct comparison
                         if new_value != old_value:
                             has_changes = True
                             logger.info(f"Change detected for {account_id} on {key}: {old_value} -> {new_value}")
                             break
                
                if not has_changes:
                    logger.info(f"No changes detected for Account {account_id}. Skipping update.")
                    return existing_record

                logger.info(f"Record for Account {account_id} already exists, updating...")
            
            # Use upsert to prevent duplicates based on account_id
            # If account_id exists, it will update the record
            # If not, it will insert a new one
            data, count = self.supabase.table(self.table_name).upsert(
                payload,
                on_conflict='account_id'  # Specify the unique constraint column
            ).execute()
            
            if existing_record:
                logger.info(f"Updated existing record for Account {account_id}")
            else:
                logger.info(f"Inserted new record for Account {account_id}")
            
            return data
        except Exception as e:
            logger.error(f"Failed to upsert record to Supabase: {e}")
            # We explicitly swallow the error to not block the pipeline
            return None

    def upsert_record(self, record: Dict[str, Any], unique_key: str = "Account_ID") -> Optional[Any]:
        """Upserts a record based on a unique key (default Account_ID)."""
        try:
            data, count = self.supabase.table(self.table_name).upsert(record).execute()
            return data
        except Exception as e:
            logger.error(f"Failed to upsert record to Supabase: {e}")
            return None

    def get_all_account_ids(self) -> List[str]:
        """
        Retrieve all Account_IDs that have been processed.
        Useful for checking what's already in the database.
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("account_id")\
                .execute()
            
            return [record['account_id'] for record in result.data]
        except Exception as e:
            logger.error(f"Error retrieving account IDs: {e}")
            return []

    def get_enrichment_stats(self) -> Dict[str, int]:
        """
        Get statistics about enrichment results.
        Returns counts by status.
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("status")\
                .execute()
            
            stats = {}
            for record in result.data:
                status = record.get('status', 'UNKNOWN')
                stats[status] = stats.get(status, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            return {}

    def insert_history_record(self, record: Dict[str, Any]) -> None:
        """
        Inserts a record into the enrichment_history table.
        This is a append-only log.
        """
        try:
            # Create copy and clean up
            payload = record.copy()
            if 'timestamp' in payload:
                del payload['timestamp']
            
            # Ensure we don't try to insert 'id' if it's auto-generated, unless we want to link it?
            # usually we just dump the data.
            
            self.supabase.table(self.history_table_name).insert(payload).execute()
        except Exception as e:
            logger.error(f"Failed to insert history record: {e}")

    def get_unsynced_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch records from enrichment_results where sync_status is 'PENDING'.
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("sync_status", "PENDING")\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching unsynced records: {e}")
            return []

    def update_sync_status(self, account_id: str, status: str) -> bool:
        """
        Update the sync_status for a specific account.
        """
        try:
            self.supabase.table(self.table_name)\
                .update({"sync_status": status})\
                .eq("account_id", account_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update sync status for {account_id}: {e}")
            return False


def get_db_client() -> SupabaseClient:
    """Factory function to create a SupabaseClient instance."""
    return SupabaseClient()

