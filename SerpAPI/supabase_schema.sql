-- Supabase Schema Update for Enrichment Results
-- PostgreSQL automatically converts unquoted identifiers to lowercase
-- So we use lowercase names for consistency

-- Drop the old table if it exists (BE CAREFUL - this will delete existing data)
DROP TABLE IF EXISTS enrichment_results;

-- Create the enrichment_results table with correct schema (lowercase names)
CREATE TABLE enrichment_results (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Account Information (lowercase column names)
    account_id TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    
    -- Google Data (lowercase column names)
    google_place_id TEXT,
    title TEXT,
    address TEXT,
    google_type__c TEXT,
    google_rating__c NUMERIC(16, 2),
    google_reviews__c INTEGER,
    google_price__c TEXT,
    google_url__c TEXT,
    
    -- Create unique constraint on account_id to prevent duplicates
    CONSTRAINT unique_account_enrichment UNIQUE (account_id)
);

-- Create index on account_id for faster lookups
CREATE INDEX idx_account_id ON enrichment_results(account_id);

-- Create index on status for filtering
CREATE INDEX idx_status ON enrichment_results(status);

-- Create index on created_at for time-based queries
CREATE INDEX idx_created_at ON enrichment_results(created_at);

-- Add comment to table
COMMENT ON TABLE enrichment_results IS 'Stores results from Salesforce account enrichment via SerpAPI';

-- Add comments to important columns
COMMENT ON COLUMN enrichment_results.account_id IS 'Salesforce Account ID (unique identifier)';
COMMENT ON COLUMN enrichment_results.status IS 'Enrichment status: ENRICHED, SKIPPED_SANITY_CHECK, NO_RESULT, ERROR';
COMMENT ON COLUMN enrichment_results.google_place_id IS 'Google Maps Place ID';
