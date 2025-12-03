"""
Download SQLite databases from jupyter/github-data releases.

This script fetches the latest release from the jupyter/github-data repository
and downloads the SQLite database files to a local directory for analysis.
"""

import os
from pathlib import Path
import requests
from subprocess import run
import sys

# Define paths
here = Path(__file__).parent
data_dir = here / "../data/jupyter"
data_dir.mkdir(exist_ok=True)

# GitHub API endpoint for latest release
REPO = "jupyter/github-data"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

# Get GitHub token if available (to avoid rate limits)
auth_keys = ["TOKEN_GITHUB_READONLY", "GITHUB_TOKEN"]
headers = {}
for key in auth_keys:
    if key in os.environ:
        headers["Authorization"] = f"token {os.environ[key]}"
        break

print(f"Fetching latest release from {REPO}...")
response = requests.get(API_URL, headers=headers)
response.raise_for_status()

release = response.json()
release_tag = release["tag_name"]
published_at = release["published_at"]

print(f"Latest release: {release_tag} (published {published_at})")

# Download all .db files from release assets
assets = release.get("assets", [])
db_files = [asset for asset in assets if asset["name"].endswith(".db")]

if not db_files:
    print("No .db files found in release assets!")
    sys.exit(1)

print(f"Found {len(db_files)} database file(s)")

for asset in db_files:
    filename = asset["name"]
    download_url = asset["browser_download_url"]
    local_path = data_dir / filename

    # Check if file already exists
    if local_path.exists():
        print(f"  {filename} already exists, skipping...")
        continue

    print(f"  Downloading {filename}...")
    file_response = requests.get(download_url, stream=True)
    file_response.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"  Saved to {local_path}")

# Save release metadata
metadata_path = data_dir / "release_info.txt"
with open(metadata_path, "w") as f:
    f.write(f"Release: {release_tag}\n")
    f.write(f"Published: {published_at}\n")

print(f"\nDownload complete! Data saved to: {data_dir.resolve()}")
print(f"Release info: {metadata_path}")
