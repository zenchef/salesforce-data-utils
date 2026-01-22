"""
Utility script to check Supabase database for duplicates and statistics.
"""
import sys
sys.path.insert(0, 'src')

from supabase_client import get_db_client

def main():
    print("Connecting to Supabase...")
    db_client = get_db_client()
    
    print("\n" + "="*60)
    print("ENRICHMENT STATISTICS")
    print("="*60)
    
    # Get stats
    stats = db_client.get_enrichment_stats()
    
    if stats:
        total = sum(stats.values())
        print(f"\nTotal Records: {total}")
        print("\nBreakdown by Status:")
        for status, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {status:25s}: {count:5d} ({percentage:5.1f}%)")
    else:
        print("\nNo records found in database.")
        return
    
    print("\n" + "="*60)
    print("DUPLICATE CHECK")
    print("="*60)
    
    # Get all account IDs
    all_ids = db_client.get_all_account_ids()
    
    # Check for duplicates (shouldn't happen with unique constraint)
    id_counts = {}
    for account_id in all_ids:
        id_counts[account_id] = id_counts.get(account_id, 0) + 1
    
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} duplicate Account_IDs:")
        for account_id, count in duplicates.items():
            print(f"  {account_id}: {count} occurrences")
    else:
        print("\n✅ No duplicates found! All Account_IDs are unique.")
    
    print("\n" + "="*60)
    print("SAMPLE RECORDS")
    print("="*60)
    
    # Show a few sample records
    print("\nRecent enriched accounts (sample):")
    try:
        result = db_client.supabase.table(db_client.table_name)\
            .select("account_id, status, title, google_rating__c, google_reviews__c")\
            .eq("status", "ENRICHED")\
            .limit(5)\
            .execute()
        
        if result.data:
            for i, record in enumerate(result.data, 1):
                print(f"\n{i}. Account: {record.get('account_id')}")
                print(f"   Title: {record.get('title', 'N/A')}")
                print(f"   Rating: {record.get('google_rating__c', 'N/A')} ({record.get('google_reviews__c', 0)} reviews)")
        else:
            print("  No enriched records found.")
    except Exception as e:
        print(f"  Error fetching samples: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
