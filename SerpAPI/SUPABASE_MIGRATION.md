# Supabase Schema Update Instructions

## Step 1: Connect to Supabase

Go to your Supabase project: https://supabasekong-m4cg0c04co488kkkw0w8wgs4.coolify.harmel.tech

## Step 2: Run the SQL Migration

1. Open the SQL Editor in Supabase
2. Copy the contents of `supabase_schema.sql`
3. Paste and execute the SQL

**⚠️ WARNING**: The SQL script will DROP the existing `enrichment_results` table and recreate it. This will delete all existing data in that table.

### Alternative: Keep Existing Data

If you want to keep existing data, use this migration instead:

```sql
-- Rename columns to match new schema
ALTER TABLE enrichment_results 
  RENAME COLUMN "Restaurant_Type__c" TO "Google_Type__c";

ALTER TABLE enrichment_results 
  RENAME COLUMN "Google_Review_Count__c" TO "Google_Reviews__c";

-- Add unique constraint on Account_ID to prevent duplicates
ALTER TABLE enrichment_results 
  ADD CONSTRAINT unique_account_enrichment UNIQUE (Account_ID);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_account_id ON enrichment_results(Account_ID);
CREATE INDEX IF NOT EXISTS idx_status ON enrichment_results(Status);
CREATE INDEX IF NOT EXISTS idx_created_at ON enrichment_results(created_at);
```

## Step 3: Verify Schema

Run this query to confirm the schema:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'enrichment_results'
ORDER BY ordinal_position;
```

## Step 4: Test the Changes

Run a dry-run to confirm Supabase logging works:

```bash
python3 src/main.py --dry-run --limit 3
```

## Features Enabled

✅ **Duplicate prevention**: Records with same Account_ID will be updated instead of creating duplicates
✅ **Correct field names**: Matches current Python code (`Google_Reviews__c`, `Google_Type__c`)
✅ **Indexed lookups**: Fast queries on Account_ID, Status, and created_at
✅ **Automatic timestamps**: created_at populated automatically
