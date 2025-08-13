# ripe-atlas-anchor-mesh-ids

A command-line script to fetch and paginate through measurement lists from the RIPE Atlas API.

This script includes features for efficient and secure data gathering. It automatically handles API pagination and rate-limiting, making it suitable for researchers, network operators, and anyone working with RIPE Atlas data.

---

## Features

- **Automatic Pagination** – Fetches all pages of a result set.
- **Automatic Retries** – Retries on common network errors or API rate limits (HTTP 429, 5xx) with a backoff delay.
- **Secure API Key Handling** – Multiple methods to use a RIPE Atlas API key, prioritizing interactive prompts and environment variables.
- **Multiple Output Formats** – Saves results as:
  - IDs (`ids`)
  - JSON Lines (`jsonl`)
  - Comma-Separated Values (`csv`)
- **API-side Filtering** – Use API filters for fields, tags, type, address family, and more to reduce download size.
- **Resume and Early Stop** – Resume an interrupted download or stop early when a minimum measurement ID is reached.

---

## Installation

1. **Prerequisites:** Python 3.6 or newer.
2. **Dependencies:** Requires the `requests` library.
   ```bash
   pip install requests
   ```

---

## Usage

Run the script with command-line arguments.

### Basic Examples

1. **Get a list of measurement IDs for default ping measurements**
   ```bash
   python3 get_measurement_ids.py --output ids > measurement_ids.txt
   ```

2. **Fetch full JSON objects for ongoing IPv6 traceroute measurements**
   ```bash
   python3 get_measurement_ids.py --type traceroute --af 6 --extra '{"status": 2}' --output jsonl -o traceroutes.jsonl
   ```

3. **Find new measurements since your last check**
   ```bash
   python3 get_measurement_ids.py --min-id 60000000 > new_measurements.txt
   ```

---

## Fetching Anchor-Related Measurements

There are two different ways to get RIPE Atlas Anchor-related data.

### 1. Anchoring Mesh (`--endpoint anchor-measurements`)

This endpoint returns measurements from the automated system where high-capacity anchors systematically measure each other to monitor core Internet health.

The total number of measurements is determined by:

```
Total Measurements = N * (N - 1) * 4
```

- `N` – Number of active anchors.
- `(N - 1)` – Each anchor measures every other anchor.
- `4` – Four tests between each pair:
  - ping/IPv4
  - ping/IPv6
  - traceroute/IPv4
  - traceroute/IPv6

**Important:** You must request the `measurement` field to get IDs.

Example:
```bash
python3 get_measurement_ids.py --endpoint anchor-measurements --fields "measurement" --output ids
```

---

### 2. Measurements Targeting an Anchor (`--tags "anchoring"`)

Find any public measurement (not just from the mesh) that targets an anchor.

Example:
```bash
python3 get_measurement_ids.py --tags "anchoring"
```

---

## Filtering Anchor Mesh Results

The RIPE Atlas API does not allow server-side filtering of the `anchor-measurements` endpoint by type (e.g., ping/traceroute). Filtering must be done locally.

### Step 1 – Fetch data with type info
```bash
python3 get_measurement_ids.py --endpoint anchor-measurements --output jsonl --fields "measurement,type,af" > all_anchor_data.jsonl
```

### Step 2 – Filter locally
```bash
# Ping only
grep '"type": "ping"' all_anchor_data.jsonl > ping_measurements.jsonl

# Traceroute only
grep '"type": "traceroute"' all_anchor_data.jsonl > traceroute_measurements.jsonl

# IPv4 pings only
grep '"type": "ping"' all_anchor_data.jsonl | grep '"af": 4' > ipv4_ping_measurements.jsonl
```

---

## Using an API Key

Using an API key provides higher rate limits.

**Option 1 – Interactive Prompt (most secure):**
```bash
python3 get_measurement_ids.py --prompt-key
```

**Option 2 – Environment Variable (good for automation):**
```bash
export RIPE_ATLAS_API_KEY="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
python3 get_measurement_ids.py
```

---

## Full Command-Line Options

```
usage: get_measurement_ids.py [-h] [--endpoint {measurements,anchor-measurements}] [--type TYPE] [--af {4,6}]
                              [--tags TAGS] [--sort SORT] [--page-size PAGE_SIZE] [--fields FIELDS] [--extra EXTRA]
                              [--output {ids,jsonl,csv}] [--outfile OUTFILE] [--timeout TIMEOUT] [--sleep SLEEP]
                              [--resume-url RESUME_URL] [--min-id MIN_ID] [--prompt-key] [--api-key API_KEY]

RIPE Atlas measurement paginator

optional arguments:
  -h, --help            Show help message and exit
  --endpoint {measurements,anchor-measurements}
                        Which list endpoint to use (default: measurements)
  --type TYPE           Measurement type (only for 'measurements' endpoint)
  --af {4,6}            Address family (only for 'measurements' endpoint)
  --tags TAGS           Comma-separated tags (only for 'measurements' endpoint)
  --sort SORT           Sort order (e.g., -id or id) (default: -id)
  --page-size PAGE_SIZE Items per page (API max usually 500) (default: 500)
  --fields FIELDS       Fields to request (use 'measurement' for anchor-measurements ID)
  --extra EXTRA         Extra query params as JSON, e.g. '{"status":1}'
  --output {ids,jsonl,csv}
                        Output format (default: ids)
  --outfile OUTFILE     Output file path or '-' for stdout (default: -)
  --timeout TIMEOUT     HTTP timeout in seconds (default: 30)
  --sleep SLEEP         Optional sleep between pages in seconds (default: 0.0)
  --resume-url RESUME_URL
                        Start from a previously captured 'next' URL
  --min-id MIN_ID       Stop early when sorted by -id and ID < this value (default: 0)

API key options (most secure first):
  --prompt-key          Prompt for API key interactively and securely.
  --api-key API_KEY     API key (WARNING: insecure; prefer --prompt-key or env var).
```
