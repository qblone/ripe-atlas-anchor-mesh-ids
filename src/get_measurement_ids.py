#!/usr/bin/env python3
"""
A command-line tool to fetch and paginate through RIPE Atlas measurement results.

This script provides features for efficient and secure data gathering from the
RIPE Atlas API. It automatically handles pagination, retries on network errors,
and can query different endpoints like the main measurements list and the
specialized anchor-measurements list.

Usage Examples:
  # Fetch default ping measurements as a list of IDs.
  python3 get_measurement_ids.py --output ids > measurement_ids.txt

  # Fetch all measurements from the Anchoring Mesh and save as CSV.
  # Note: No type/af/tags filters are used for this endpoint.
  python3 get_measurement_ids.py --endpoint anchor-measurements --fields "id,measurement,probe_id" --output csv

  # Fetch new traceroute measurements using a securely provided API key.
  python3 get_measurement_ids.py --type traceroute --min-id 60000000 --prompt-key
"""
import argparse
import csv
import getpass
import json
import logging
import os
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Define API constants
DEFAULT_URL = "https://atlas.ripe.net/api/v2/measurements/"
ANCHOR_URL = "https://atlas.ripe.net/api/v2/anchor-measurements/"


def make_session(total_retries=5, backoff_factor=0.5, ua="atlas-fetch/1.0", api_key=None):
    """
    Creates a requests.Session with retry settings and optional API key auth.

    Args:
        total_retries (int): The total number of retries to allow.
        backoff_factor (float): A factor to apply between retry attempts.
        ua (str): The User-Agent string for the request.
        api_key (str, optional): The RIPE Atlas API key. Defaults to None.

    Returns:
        requests.Session: A configured session object.
    """
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),  # Status codes to retry on
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    s = requests.Session()
    headers = {"User-Agent": ua, "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Key {api_key}"

    s.headers.update(headers)
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def parse_args():
    """
    Defines and parses all command-line arguments for the script.

    Returns:
        argparse.Namespace: An object containing all parsed arguments.
    """
    p = argparse.ArgumentParser(
        description="RIPE Atlas measurement paginator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--endpoint", choices=["measurements", "anchor-measurements"], default="measurements",
                   help="Which list endpoint to use")
    p.add_argument("--type", default="ping", help="Measurement type (only for 'measurements' endpoint)")
    p.add_argument("--af", type=int, choices=[4, 6], default=4, help="Address family (only for 'measurements' endpoint)")
    p.add_argument("--tags", default="anchoring,probes", help="Comma-separated tags (only for 'measurements' endpoint)")
    p.add_argument("--sort", default="-id", help="Sort order (e.g., -id or id)")
    p.add_argument("--page-size", type=int, default=500, help="Items per page (API max is usually 500)")
    p.add_argument("--fields", default="id", help="Fields to request (use 'measurement' for anchor-measurements ID)")
    p.add_argument("--extra", default="", help="Extra query params as JSON, e.g. '{\"status\":1}'")
    p.add_argument("--output", choices=["ids", "jsonl", "csv"], default="ids", help="Output format")
    p.add_argument("--outfile", default="-", help="Output file path or '-' for stdout")
    p.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    p.add_argument("--sleep", type=float, default=0.0, help="Optional sleep between pages (seconds)")
    p.add_argument("--resume-url", default="", help="Start from a previously captured 'next' URL")
    p.add_argument("--min-id", type=int, default=0, help="Stop early when sorted by -id and ID is less than this value")

    key_group = p.add_argument_group('API Key Options (most secure first)')
    key_group.add_argument("--prompt-key", action="store_true", help="Prompt for API key interactively and securely.")
    key_group.add_argument("--api-key", help="API key (WARNING: insecure. Prefer --prompt-key or RIPE_ATLAS_API_KEY env var).")
    return p.parse_args()


def get_api_key(args):
    """
    Gets API key from the safest source available (prompt, env var, or arg).

    Args:
        args (argparse.Namespace): The parsed command-line arguments.

    Returns:
        str or None: The API key if found, otherwise None.
    """
    if args.prompt_key:
        try:
            return getpass.getpass("Enter RIPE Atlas API Key: ")
        except (EOFError, KeyboardInterrupt):
            logging.warning("\nAPI key entry cancelled.")
            sys.exit(1)

    key_from_env = os.getenv('RIPE_ATLAS_API_KEY')
    if key_from_env:
        logging.info("Using API key from RIPE_ATLAS_API_KEY environment variable.")
        return key_from_env

    if args.api_key:
        logging.warning("Using API key from command-line argument. This is insecure!")
        return args.api_key

    return None


def open_out(path):
    """
    Opens the given file path for writing or returns sys.stdout if path is '-'.

    Args:
        path (str): The file path or '-'.

    Returns:
        A file-like object ready for writing.
    """
    return sys.stdout if path == "-" else open(path, "w", newline="", encoding="utf-8")


def main():
    """
    Main execution function.

    Orchestrates argument parsing, session creation, API requests, and result
    processing. It conditionally builds API parameters based on the selected
    endpoint to ensure compatibility.
    """
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)

    api_key = get_api_key(args)
    session = make_session(api_key=api_key)

    # --- Determine endpoint and the correct field name for the measurement ID ---
    if args.endpoint == "anchor-measurements":
        base = ANCHOR_URL
        # The ID of an anchor-measurement result is its own unique ID.
        # The ID of the actual measurement it represents is in the 'measurement' field.
        # Default to 'measurement' if user wants IDs, otherwise use the object's own 'id'.
        id_key = "measurement" if args.output == "ids" else "id"
    else:
        base = DEFAULT_URL
        id_key = "id"

    # --- Build API parameters based on endpoint compatibility ---
    # Start with params that are common to all endpoints
    params = {
        "sort": args.sort,
        "page_size": args.page_size,
        "fields": args.fields,
    }

    # Conditionally add filters that are only supported by the 'measurements' endpoint
    if args.endpoint == "measurements":
        params["type"] = args.type
        params["af"] = args.af
        params["tags"] = args.tags

    # Add any extra user-defined parameters
    if args.extra:
        try:
            params.update(json.loads(args.extra))
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in --extra argument: {e}")
            sys.exit(1)

    url = args.resume_url if args.resume_url else base
    out = open_out(args.outfile)
    writer = None  # CSV writer is initialized on the first result
    is_ids_only = (args.output == "ids")
    page_count = 0

    try:
        # Loop as long as the API provides a 'next' URL for pagination
        while url:
            page_count += 1
            logging.info(f"Fetching page {page_count}...")
            # Params are only sent on the first request; 'next' URL contains them
            r = session.get(url, params=params if url == base else None, timeout=args.timeout)
            r.raise_for_status()  # Raise an exception for HTTP errors not handled by Retry
            data = r.json()
            results = data.get("results", [])
            logging.info(f"Successfully fetched {len(results)} results.")

            if not results:
                logging.info("No more results, stopping.")
                break

            # Process and write results based on the chosen output format
            for item in results:
                if is_ids_only:
                    print(item.get(id_key), file=out)
                elif args.output == "jsonl":
                    out.write(json.dumps(item) + "\n")
                else:  # csv
                    if writer is None:
                        fieldnames = sorted(item.keys())
                        writer = csv.DictWriter(out, fieldnames=fieldnames)
                        writer.writeheader()
                    writer.writerow(item)

            # Early stop logic for fetching recent measurements
            if args.min_id and args.sort.strip() == "-id":
                ids = [x.get(id_key) for x in results if isinstance(x.get(id_key), int)]
                if ids and min(ids) < args.min_id:
                    logging.info(f"Stopping early: found ID {min(ids)}, which is < --min-id {args.min_id}.")
                    break

            url = data.get("next")
            params = {}  # Clear params after first request
            if url and args.sleep > 0:
                logging.info(f"Sleeping for {args.sleep} seconds.")
                time.sleep(args.sleep)

    except requests.exceptions.RequestException as e:
        logging.error(f"An HTTP request failed: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        # Ensure the output file is closed if it's not stdout
        logging.info("Script finished.")
        if out is not sys.stdout:
            out.close()


if __name__ == "__main__":
    main()
