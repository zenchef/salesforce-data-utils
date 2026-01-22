-- Migration to add new columns for Google Extensions and Status
-- Run this in your Supabase SQL Editor

ALTER TABLE enrichment_results
ADD COLUMN IF NOT EXISTS prospection_status__c TEXT,
ADD COLUMN IF NOT EXISTS has_google_accept_bookings_extension__c BOOLEAN,
ADD COLUMN IF NOT EXISTS has_google_delivery_extension__c BOOLEAN,
ADD COLUMN IF NOT EXISTS has_google_takeout_extension__c BOOLEAN;

COMMENT ON COLUMN enrichment_results.prospection_status__c IS 'Permanently Closed or Temporarily Closed';
COMMENT ON COLUMN enrichment_results.has_google_delivery_extension__c IS 'True if Google output indicates delivery available';
