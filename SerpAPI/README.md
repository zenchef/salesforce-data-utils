
# Salesforce Enrichment Tool (SerpApi + Supabase)

This tool enriches Salesforce Accounts with Google My Business data (via SerpApi) and logs results to both a local CSV and a Supabase database.

## Features

-   **Enrichment**: Fetches Google My Business data for Salesforce Accounts missing `Google_Place_ID__c`.
    -   Fetches: Rating, Reviews, Price, Type, Website, Photos, Booking options.
    -   **Filters**: Excludes accounts marked as "Hotel" OR `RecordType` = "Parent".
-   **Sanity Check**: Ensures high-quality matching.
    -   Compares Salesforce `Name` OR `Nom_du_restaurant__c` with Google Maps Title.
    -   **Rule**: Enrichment proceeds if **EITHER field** has **≥ 80% similarity**. If both are lower, the account is skipped.
-   **Logging**:
    -   Database: **Supabase** (`enrichment_results` table) with duplicate prevention.
    -   *Note: Local CSV logging has been removed.*
-   **Performance**: Multi-threaded processing for volume.
-   **Duplicate Prevention**: Unique constraint on `account_id` prevents duplicate enrichment logs.

## Logic Overview

1.  **Fetch**: Gets accounts from Salesforce where `Google_Place_ID__c` is null. Excludes `RecordType = 'Parent'` and `Hotel_Restaurant__c = true`.
2.  **Search**: Queries Google Maps with `Name + Address + City + Country + "Restaurant"`.
3.  **Validate**: Fuzzy match check comparing Google Title with BOTH `Name` AND `Nom_du_restaurant__c`. Enrichment proceeds if EITHER field scores ≥80%.
4.  **Clean Data**: 
        - **Price**: Normalizes to Salesforce picklist format ($, $$, $$$, $$$$). 
            - **Logic**: Handles specific values (`€20`) and ranges (`€20–30`). For ranges, the **average** value is calculated to determine the price level.
        - **Type**: Converts arrays to comma-separated strings (e.g., `['Restaurant', 'Cafe']` → `"Restaurant, Cafe"`).

    ## Directory Structure
    ```text
    /serpAPI/
    ├── src/                    # Source code
    │   ├── main.py             # Entry point
    │   ├── config.py           # Config & Auth
    │   ├── supabase_client.py  # DB Connector (with duplicate checking)
    │   ├── salesforce_client.py # Salesforce API client
    │   ├── serp_client.py      # SerpApi client
    │   └── enrichment_service.py # Core enrichment logic
    ├── data/                   # Output CSVs
    ├── logs/                   # Application logs
    ├── check_database.py       # Utility to check Supabase stats
    ├── supabase_schema.sql     # Database schema
    ├── .env                    # Credentials
    └── requirements.txt
    ```

    ## Salesforce Fields Updated

    | Field Name | Type | Description |
    |-----------|------|-------------|
    | `Google_Place_ID__c` | Text(255) | Google Maps Place ID (External ID) |
    | `Google_Data_ID__c` | Text(255) | Google Data ID (External ID) |
    | `Google_Type__c` | Text(255) | Restaurant type (e.g., "French restaurant, Bistro") |
    | `Google_Rating__c` | Number(16,2) | Average rating from Google |
    | `Google_Reviews__c` | Number(18,0) | Number of reviews |
    | `Google_Price__c` | Picklist | Price level ($, $$, $$$, $$$$) |
    | `Google_Updated_Date__c` | Date | Date the Google data was fetched |
    | `Google_Thumbnail_URL__c` | URL(255) | Thumbnail image URL |
    | `Google_URL__c` | URL(255) | Restaurant website URL |
    | `Has_Google_Accept_Bookings_Extension__c` | Checkbox | Google bookings available |
    | `HasGoogleDeliveryExtension__c` | Checkbox | Delivery available (from service options) |
    | `HasGoogleTakeoutExtension__c` | Checkbox | Takeout available (from service options) |
    | `Prospection_Status__c` | Picklist | Status ("Permanently Closed", "Temporarily Closed") |
    | `BillingStreet` | Address | Updated for prospects if high match |

    ## Prerequisites

    -   Python 3.8+
    -   Salesforce Credentials
    -   SerpApi Key
    -   Supabase Project (URL + Key)

    ## Installation

    1.  Install dependencies:
        ```bash
        pip3 install -r requirements.txt
        ```

    2.  **Configuration**: Set up your environment variables by copying the example file:
        
        ```bash
        cp example.env .env
        ```
        
        Then open `.env` and fill in your credentials:

        ```env
        # Salesforce
        DOMAIN=login
        CONSUMER_KEY=your_consumer_key
        CONSUMER_SECRET=your_consumer_secret
        USERNAME=your_username
        PASSWORD=your_password
        SECURITY_TOKEN=your_security_token

        # SERP API
        SERPAPI_KEY=your_serpapi_key

        # Supabase
        SUPABASE_URL=your_supabase_url
        SUPABASE_KEY=your_supabase_key
        ```

    3.  **Supabase Setup**:
        
        If setting up for the first time:
        ```bash
        # Run the main schema
        cat supabase_schema.sql
        ```
        
        **CRITICAL UPDATE**: If you already have the table, you MUST run the migration to add new columns:
        ```bash
        # Open Supabase SQL Editor and run the contents of:
        cat add_fields_migration.sql
        ```

    ## Usage

    **Note**: Always run from the root directory.

    ### 1. Check Database Stats
    View enrichment statistics and check for duplicates:
    ```bash
    python3 check_database.py
    ```

    ### 2. Dry Run (Recommended)
    Simulate the process. Logs to Supabase.
    ```bash
    python3 src/main.py --dry-run
    ```

    ### 3. Test with Limit
    Process only a few accounts to verify.
    ```bash
    python3 src/main.py --dry-run --limit 10
    ```

    ### 4. Production Run (Large Scale)
    To process all 50,000+ accounts, simply run the script. It now uses "Seek Pagination" to iterate through all records efficiently and checks Supabase before calling the API to skip already enriched accounts.
    ```bash
    python3 src/main.py
    ```
    *Note: You can stop and restart the script at any time. It will fast-forward through already enriched accounts.*

    ## Output

    ### Supabase Table: `enrichment_results`
    | Column | Type | Description |
    |--------|------|-------------|
    | `account_id` | TEXT | Salesforce ID (unique) |
    | `status` | TEXT | `ENRICHED`, `SKIPPED_SANITY_CHECK`, `NO_RESULT`, `ERROR` |
    | `message` | TEXT | Status details |
    | `title` | TEXT | Google Maps Title |
    | `address` | TEXT | Google Maps Address |
    | `google_place_id` | TEXT | Matched Place ID |
    | `google_type__c` | TEXT | Restaurant type(s) |
    | `google_rating__c` | NUMERIC | Rating (0-5) |
    | `google_reviews__c` | INTEGER | Review count |
    | `google_price__c` | TEXT | Price level |
    | `google_url__c` | TEXT | Website URL |
    | `created_at` | TIMESTAMP | Auto-timestamp |

    **Unique Constraint**: `account_id` - prevents duplicate logs.

    ## Status Codes

    - **ENRICHED**: Successfully enriched account with Google data
    - **SKIPPED_SANITY_CHECK**: Fuzzy match score < 80% (data quality protection)
    - **NO_RESULT**: No Google Maps results found for search query
    - **ERROR**: Error occurred during processing

    ## Quality Metrics

    From recent runs, the fuzzy matching protection successfully prevents ~65-80% of low-confidence matches, ensuring only high-quality data enriches Salesforce.

    ## Troubleshooting

    **Issue**: Supabase errors about missing columns  
    **Solution**: Run the updated `supabase_schema.sql` migration

    **Issue**: Account_ID showing as `None` in logs  
    **Solution**: This is expected behavior - the account_id is extracted from the CSV entry internally

    **Issue**: High percentage of SKIPPED_SANITY_CHECK  
    **Solution**: This is normal - the 80% threshold protects data quality. Review skipped accounts manually if needed.

    ## Files

    - `src/main.py` - Entry point and orchestration
    - `src/enrichment_service.py` - Core enrichment logic
    - `src/salesforce_client.py` - Salesforce API wrapper
    - `src/serp_client.py` - SerpApi wrapper with array-to-string conversion
    - `src/supabase_client.py` - Supabase client with duplicate checking
    - `src/config.py` - Configuration and authentication
    - `check_database.py` - Database statistics utility
    - `supabase_schema.sql` - Database schema (lowercase columns)
    - `SUPABASE_MIGRATION.md` - Migration instructions
