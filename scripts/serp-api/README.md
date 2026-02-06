
# Salesforce Enrichment Tool (SerpApi)

This tool enriches Salesforce Accounts with Google Maps data (via SerpApi) and updates them directly in Salesforce. Every run is logged to a timestamped CSV for audit.

## Features

-   **Enrichment**: Fetches Google Maps data for Salesforce Accounts missing `Google_Place_ID__c`.
    -   Fetches: Rating, Reviews, Price, Type, Website, Thumbnail, Booking options.
    -   **Filters**: Excludes accounts marked as "Hotel" OR `RecordType` = "Parent".
-   **Sanity Check**: Ensures high-quality matching.
    -   Compares Salesforce `Name` OR `Nom_du_restaurant__c` with Google Maps Title.
    -   **Rule**: Enrichment proceeds if **EITHER field** has **>= 80% similarity**. If both are lower, the account is skipped.
-   **Logging**: Every processed account is logged to a timestamped CSV in `data/` (at repo root).
-   **Performance**: Multi-threaded processing (20 workers) with batched seek pagination.
-   **Dynamic Query**: Only fetches accounts where `Google_Place_ID__c` is null, so re-running is safe.

## Logic Overview

1.  **Fetch**: Gets accounts from Salesforce where `Google_Place_ID__c` is null. Excludes `RecordType = 'Parent'` and `Hotel_Restaurant__c = true`.
2.  **Search**: Queries Google Maps with `Name + Address + City + Country + "Restaurant"`.
3.  **Validate**: Fuzzy match check comparing Google Title with BOTH `Name` AND `Nom_du_restaurant__c`. Enrichment proceeds if EITHER field scores >= 80%.
4.  **Clean Data**:
    - **Price**: Normalizes to Salesforce picklist format ($, $$, $$$, $$$$).
        - **Logic**: Handles specific values (`€20`) and ranges (`€20-30`). For ranges, the **average** value is calculated to determine the price level.
    - **Type**: Converts arrays to comma-separated strings (e.g., `['Restaurant', 'Cafe']` -> `"Restaurant, Cafe"`).
5.  **Update**: Writes enriched data directly to Salesforce Account fields (unless `--dry-run`).
6.  **Log**: Writes a row to the CSV with status, match score, and all Google data.

## Directory Structure

```text
salesforce-data-utils/
├── .env                          # Credentials (gitignored, at repo root)
├── .env.example                  # Credentials template
├── .gitignore                    # Single gitignore for the whole repo
├── requirements.txt              # Python dependencies
├── data/                         # Output CSVs (gitignored)
└── scripts/
    └── serp-api/
        ├── main.py               # Entry point & orchestration
        ├── config.py             # Config & Auth
        ├── salesforce_client.py  # Salesforce API client
        ├── serp_client.py        # SerpApi client
        └── enrichment_service.py # Core enrichment logic + CSV logging
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
| `HasGoogleAcceptBookingsExtension__c` | Checkbox | Google bookings available |
| `HasGoogleDeliveryExtension__c` | Checkbox | Delivery available (from service options) |
| `HasGoogleTakeoutExtension__c` | Checkbox | Takeout available (from service options) |
| `Prospection_Status__c` | Picklist | Status ("Permanently Closed", "Temporarily Closed") |

## Prerequisites

-   Python 3.8+
-   Salesforce Credentials (Username, Password, Security Token)
-   SerpApi Key ([serpapi.com](https://serpapi.com/))

## Installation

1.  Install dependencies (from repo root):
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**: Set up your environment variables by copying the example file:

    ```bash
    cp .env.example .env
    ```

    Then open `.env` at the repo root and fill in your credentials:

    ```env
    # Salesforce
    SF_USERNAME=your_username
    SF_PASSWORD=your_password
    SF_TOKEN=your_security_token

    # SERP API
    SERPAPI_KEY=your_serpapi_key
    ```

## Usage

All commands are run from the repo root.

### 1. Dry Run (Recommended first)
Simulate the process. Searches Google Maps and logs to CSV but does **not** update Salesforce.
```bash
python scripts/serp-api/main.py --dry-run --limit 10
```

### 2. Test with Limit
Process only a few accounts to verify everything works.
```bash
python scripts/serp-api/main.py --limit 10
```

### 3. Full Run
Process all unenriched accounts. Uses seek pagination to handle 50,000+ accounts in batches of 1000.
```bash
python scripts/serp-api/main.py
```

## Output

Each run creates a timestamped CSV in `data/` (e.g., `data/enrichment_20260206_183000.csv`):

| Column | Description |
|--------|-------------|
| `account_id` | Salesforce Account ID |
| `account_name` | Account Name |
| `status` | `ENRICHED`, `ENRICHED (DRY RUN)`, `SKIPPED_SANITY_CHECK`, `NO_RESULT`, `SKIPPED`, `ERROR` |
| `message` | Status details |
| `google_place_id` | Matched Place ID |
| `google_title` | Google Maps Title |
| `google_address` | Google Maps Address |
| `google_type` | Restaurant type(s) |
| `google_rating` | Rating (0-5) |
| `google_reviews` | Review count |
| `google_price` | Price level |
| `google_url` | Website URL |
| `match_score` | Fuzzy match percentage |
| `matched_field` | Which SF field matched (Name or Nom_du_restaurant__c) |
| `timestamp` | Processing timestamp |

## Status Codes

- **ENRICHED**: Successfully enriched and updated in Salesforce
- **ENRICHED (DRY RUN)**: Would have been enriched (dry-run mode)
- **SKIPPED_SANITY_CHECK**: Fuzzy match score < 80% (data quality protection)
- **NO_RESULT**: No Google Maps results found for search query
- **SKIPPED**: Insufficient data to build a search query
- **ERROR**: Error occurred during processing

## Troubleshooting

**Issue**: High percentage of SKIPPED_SANITY_CHECK
**Solution**: This is normal - the 80% threshold protects data quality. Review skipped accounts manually in the CSV if needed.

**Issue**: SerpApi errors or rate limits
**Solution**: Use `--limit` to control volume. SerpApi charges per search, so start small.

## Files

- `main.py` - Entry point and orchestration
- `enrichment_service.py` - Core enrichment logic, validation, and CSV logging
- `salesforce_client.py` - Salesforce API wrapper (query, update, merge)
- `serp_client.py` - SerpApi client with result mapping
- `config.py` - Configuration and authentication
