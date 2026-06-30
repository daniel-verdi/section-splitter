"""Download Semantic Scholar dataset files for the latest S2 release.

The Semantic Scholar datasets API exposes time-limited download URLs for each
release. This script asks the API for the latest release, fetches the file URLs
for a dataset such as ``s2orc``, and downloads each part into a local folder.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import RequestException


TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_DATASET = "s2orc"
DEFAULT_REQUESTS_PER_SECOND = 1.0


def make_request_with_backoff(
    url: str,
    headers: dict[str, str],
    *,
    max_retries: int = 5,
    backoff_factor: int = 2,
) -> dict[str, Any]:
    """Return JSON from the Semantic Scholar API, retrying transient failures."""
    for retry in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=60)
        except RequestException as exc:
            wait_time = backoff_factor**retry
            print(f"Request failed: {exc}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        if response.status_code == 200:
            return response.json()

        if response.status_code in TRANSIENT_STATUS_CODES:
            wait_time = backoff_factor**retry
            print(
                f"Transient API error (HTTP {response.status_code}). "
                f"Retrying in {wait_time} seconds..."
            )
            time.sleep(wait_time)
            continue

        print(f"HTTP error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)

    print("Max retries exceeded. Exiting.", file=sys.stderr)
    sys.exit(1)


def fetch_latest_release_id(api_key: str) -> str:
    """Fetch the current Semantic Scholar dataset release identifier."""
    headers = {"x-api-key": api_key}
    url = "https://api.semanticscholar.org/datasets/v1/release/latest"
    release_data = make_request_with_backoff(url, headers)
    release_id = release_data.get("release_id")

    if not release_id:
        print("Failed to fetch latest release ID. Exiting.", file=sys.stderr)
        sys.exit(1)

    return release_id


def fetch_dataset_links(api_key: str, release_id: str, dataset_name: str) -> list[str]:
    """Fetch signed download links for one dataset in a release."""
    headers = {"x-api-key": api_key}
    url = (
        "https://api.semanticscholar.org/datasets/v1/"
        f"release/{release_id}/dataset/{dataset_name}"
    )
    dataset_data = make_request_with_backoff(url, headers)
    download_links = dataset_data.get("files", [])

    if not download_links:
        print(
            f"No files found for dataset '{dataset_name}' in release '{release_id}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    return download_links


def download_file(
    url: str,
    output_path: Path,
    *,
    max_retries: int = 5,
    backoff_factor: int = 2,
) -> bool:
    """Download one dataset part and return whether it completed successfully."""
    for retry in range(max_retries):
        try:
            with requests.get(url, stream=True, timeout=60) as response:
                if response.status_code == 200:
                    with output_path.open("wb") as file_handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                file_handle.write(chunk)
                    return True

                if response.status_code in TRANSIENT_STATUS_CODES:
                    wait_time = backoff_factor**retry
                    print(
                        f"Transient download error (HTTP {response.status_code}). "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    continue

                print(
                    f"Failed to download {output_path.name}. "
                    f"HTTP status code: {response.status_code}",
                    file=sys.stderr,
                )
                return False
        except RequestException as exc:
            wait_time = backoff_factor**retry
            print(f"Failed to download {output_path.name}: {exc}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    return False


def download_files(
    download_links: list[str],
    dataset_name: str,
    output_dir: Path,
    *,
    requests_per_second: float = DEFAULT_REQUESTS_PER_SECOND,
) -> None:
    """Download all dataset parts into ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wait_between_requests = 1.0 / requests_per_second if requests_per_second > 0 else 0

    for index, link in enumerate(download_links, start=1):
        output_path = output_dir / f"{dataset_name}_part{index}.zip"
        print(f"Downloading part {index} to {output_path}...")

        if download_file(link, output_path):
            print(f"Successfully downloaded part {index}.")
        else:
            print(f"Failed to download part {index} after multiple retries. Skipping.")

        # Semantic Scholar asks clients to keep download request rates modest.
        time.sleep(wait_between_requests)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download a Semantic Scholar dataset from the latest release."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET,
        help="Dataset to download. Default: s2orc.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("S2_API_KEY"),
        help="Semantic Scholar API key. Defaults to the S2_API_KEY environment variable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for downloaded parts. Defaults to a folder named after the dataset.",
    )
    parser.add_argument(
        "--requests-per-second",
        type=float,
        default=DEFAULT_REQUESTS_PER_SECOND,
        help="Download throttle. Default: 1 request per second.",
    )
    return parser.parse_args()


def main() -> None:
    """Download all parts for the requested dataset."""
    args = parse_args()

    if not args.api_key:
        print(
            "API key is required. Pass --api-key or set S2_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = args.output_dir or Path(args.dataset)

    print("Fetching latest release ID...")
    release_id = fetch_latest_release_id(args.api_key)
    print(f"Latest release ID: {release_id}")

    print(f"Fetching download links for dataset '{args.dataset}'...")
    download_links = fetch_dataset_links(args.api_key, release_id, args.dataset)

    print(f"Downloading {len(download_links)} parts of the '{args.dataset}' dataset...")
    download_files(
        download_links,
        args.dataset,
        output_dir,
        requests_per_second=args.requests_per_second,
    )


if __name__ == "__main__":
    main()
