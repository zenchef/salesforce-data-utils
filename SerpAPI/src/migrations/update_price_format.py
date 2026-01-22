import logging
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import get_db_client
from enrichment_service import EnrichmentService
from config import validate_config

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def update_price_format():
    """
    Iterates through all records in Supabase and updates the price format.
    """
    try:
        validate_config()
        db_client = get_db_client()
        
        # We need access to the _clean_price method, so we can instantiate EnrichmentService
        # We can pass None for dependencies we don't need for this specific method
        service = EnrichmentService(None, None, db_client)
        
        logger.info("Fetching all records from Supabase...")
        
        # Fetch all records - we might need pagination if dataset is huge, 
        # but for now let's try fetching all or use a reasonably large limit if possible.
        # Supabase client 'get_all_account_ids' only gets IDs.
        # Let's add a custom query here or rely on the client.
        # Since the client doesn't expose a 'get_all_records' method, we will use the underlying supabase client directly here for the script.
        
        # Page through results
        PAGE_SIZE = 1000
        offset = 0
        total_updated = 0
        total_processed = 0
        
        while True:
            logger.info(f"Fetching batch starting at {offset}...")
            response = db_client.supabase.table(db_client.table_name)\
                .select("account_id, google_price__c")\
                .range(offset, offset + PAGE_SIZE - 1)\
                .execute()
                
            records = response.data
            if not records:
                break
                
            for record in records:
                aid = record.get('account_id')
                raw_price = record.get('google_price__c')
                
                new_price = service._clean_price(raw_price)
                
                # Check if update is needed
                # _clean_price returns None for invalid/empty, so we should be careful not to wipe data if it was something weird but valuable (though requirement is to unify)
                # If raw_price was not None but new_price is None, it means it didn't match criteria. 
                # Ideally we only update if we produced a VALID unified price that is different.
                
                should_update = False
                if raw_price != new_price:
                    # Case 1: We have a new valid format, and it's different
                    if new_price is not None:
                        should_update = True
                    # Case 2: We verified it's invalid and want to fallback to None? 
                    # The user said "unify all notations to $, $$, ..., and update the olds one"
                    # Generally implies cleaning. If it's "1" -> "$", good. If "Cheap" -> None, maybe we leave it or clear it.
                    # I'll assume we strictly want the $, $$ format.
                    elif raw_price and new_price is None:
                        # It had a value, but we couldn't parse it. 
                        # Let's log this but maybe not clear it blindly unless asked.
                        # For now, I will strictly update only if I have a standardized value to replace it with 
                        # OR if it was a format we specifically wanted to fix (like integers).
                        pass

                if should_update:
                    logger.info(f"Updating {aid}: '{raw_price}' -> '{new_price}'")
                    
                    # Update Record
                    db_client.supabase.table(db_client.table_name)\
                        .update({"google_price__c": new_price})\
                        .eq("account_id", aid)\
                        .execute()
                    
                    total_updated += 1
            
            total_processed += len(records)
            offset += PAGE_SIZE
            
            if len(records) < PAGE_SIZE:
                break
                
        logger.info(f"Migration Complete. Processed: {total_processed}, Updated: {total_updated}")

    except Exception as e:
        logger.error(f"Migration Failed: {e}")

if __name__ == "__main__":
    update_price_format()
