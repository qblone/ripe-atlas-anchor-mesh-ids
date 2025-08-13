# ripe-atlas-anchor-mesh-ids
=============================


A command-line script to fetch and paginate through measurement lists from the RIPE Atlas API.

This script includes features for efficient and secure data gathering. It automatically handles API pagination and rate-limiting, making it suitable for researchers, network operators, and anyone working with RIPE Atlas data.

-------------------
FEATURES
-------------------

* Automatic Pagination: Fetches all pages of a result set.
* Automatic Retries: Retries the connection on common network errors or API rate limits (HTTP 429, 5xx) with a backoff delay.
* Secure API Key Handling: Provides multiple methods to use a RIPE Atlas API key, prioritizing interactive prompts and environment variables.
* Multiple Output Formats: Saves results as a simple list of IDs (ids), JSON Lines (jsonl), or Comma-Separated Values (csv).
* API-side Filtering: Uses API filters for fields, tags, type, address family, and more to reduce download size.
* Resume and Early-Stop: Can resume an interrupted download using a 'next' URL and can stop fetching when a minimum measurement ID is reached.

-------------------
INSTALLATION
-------------------

1. Prerequisites: Python 3.6 or newer.

2. Dependencies: Requires the `requests` library. Install it with pip:
   pip install requests

-------------------
USAGE
-------------------

The script is controlled via command-line arguments.

---
Basic Examples
---

1. Get a list of measurement IDs for default ping measurements.
   python3 get_measurement_ids.py --output ids > measurement_ids.txt

2. Fetch full JSON objects for ongoing IPv6 traceroute measurements.
   python3 get_measurement_ids.py --type traceroute --af 6 --extra '{"status": 2}' --output jsonl -o traceroutes.jsonl

3. Find new measurements since your last check.
   This command fetches measurements sorted by most recent (-id) and stops when it finds a measurement with an ID lower than 60000000.
   python3 get_measurement_ids.py --min-id 60000000 > new_measurements.txt

---
Fetching Anchor-Related Measurements
---

There are two different ways to get data related to RIPE Atlas Anchors.

1. The Anchoring Mesh (`--endpoint anchor-measurements`)
   This endpoint returns measurements from the automated system where high-capacity anchors systematically measure each other to monitor core internet health.

   The total number of measurements from this endpoint is very high (e.g., over 12,000) because it's a complete "full mesh" system. The count is determined by a formula based on the number of active anchors (`N`):

   `Total Measurements = N * (N - 1) * 4`

   - `N` is the number of active anchors.
   - `(N - 1)` is because each anchor measures every other anchor.
   - `4` represents the four tests run between each pair (ping/IPv4, ping/IPv6, traceroute/IPv4, traceroute/IPv6).

   **Important:** When using this endpoint, you must specify which fields you want with the `--fields` argument. To get the actual measurement IDs, you must request the `measurement` field.

   # Fetch the measurement IDs from the Anchoring Mesh
   python3 get_measurement_ids.py --endpoint anchor-measurements --fields "measurement" --output ids

2. Measurements Targeting an Anchor (`--tags "anchoring"`)
   This finds any public measurement (not just from the mesh) that *targets* an anchor. This is useful for finding tests from regular probes directed at an anchor.

   # Fetch measurements from any probe that targets an anchor
   python3 get_measurement_ids.py --tags "anchoring"

---
Filtering Anchor Mesh Results
---

The RIPE Atlas API does not allow filtering the `anchor-measurements` endpoint by type (e.g., ping, traceroute) on the server. You must download the complete dataset and filter it locally.

**Step 1: Fetch the data with type information**
Use the script to download the anchor data in `jsonl` format. You must include `measurement`, `type`, and `af` (address family) in the `--fields` argument.

   python3 get_measurement_ids.py --endpoint anchor-measurements --output jsonl --fields "measurement,type,af" > all_anchor_data.jsonl

**Step 2: Filter the downloaded file with `grep`**
Once you have the `all_anchor_data.jsonl` file, you can use standard command-line tools like `grep` to find the specific measurements you need.

   # To get only ping measurements:
   grep '"type": "ping"' all_anchor_data.jsonl > ping_measurements.jsonl

   # To get only traceroute measurements:
   grep '"type": "traceroute"' all_anchor_data.jsonl > traceroute_measurements.jsonl

   # To get only IPv4 pings:
   grep '"type": "ping"' all_anchor_data.jsonl | grep '"af": 4' > ipv4_ping_measurements.jsonl

---
Using an API Key
---

Using an API key provides higher rate limits from the API.

Option 1: Interactive Prompt (Most Secure)
   python3 get_measurement_ids.py --prompt-key

Option 2: Environment Variable (For Automated Scripts)
   export RIPE_ATLAS_API_KEY="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   python3 get_measurement_ids.py

---
Full Command-Line Options
---

usage: get_measurement_ids.py [-h] [--endpoint {measurements,anchor-measurements}] [--type TYPE] [--af {4,6}] [--tags TAGS] [--sort SORT] [--page-size PAGE_SIZE] [--fields FIELDS] [--extra EXTRA]
                              [--output {ids,jsonl,csv}] [--outfile OUTFILE] [--timeout TIMEOUT] [--sleep SLEEP] [--resume-url RESUME_URL] [--min-id MIN_ID] [--prompt-key] [--api-key API_KEY]

RIPE Atlas measurement paginator

options:
  -h, --help            show this help message and exit
  --endpoint {measurements,anchor-measurements}
                        Which list endpoint to use (default: measurements)
  --type TYPE           Measurement type (only for 'measurements' endpoint)
  --af {4,6}            Address family (only for 'measurements' endpoint)
  --tags TAGS           Comma-separated tags (only for 'measurements' endpoint)
  --sort SORT           Sort order (e.g., -id or id) (default: -id)
  --page-size PAGE_SIZE
                        Items per page (API max is usually 500) (default: 500)
  --fields FIELDS       Fields to request (use 'measurement' for anchor-measurements ID)
  --extra EXTRA         Extra query params as JSON, e.g. '{"status":1}' (default: )
  --output {ids,jsonl,csv}
                        Output format (default: ids)
  --outfile OUTFILE     Output file path or '-' for stdout (default: -)
  --timeout TIMEOUT     HTTP timeout seconds (default: 30)
  --sleep SLEEP         Optional sleep between pages (seconds) (default: 0.0)
  --resume-url RESUME_URL
                        Start from a previously captured 'next' URL (default: )
  --min-id MIN_ID       Stop early when sorted by -id and an ID is less than this value (default: 0)

API Key Options (most secure first):
  --prompt-key          Prompt for API key interactively and securely.
  --api-key API_KEY     API key (WARNING: insecure, exposed in shell history. Prefer --prompt-key or RIPE_ATLAS_API_KEY env var).

