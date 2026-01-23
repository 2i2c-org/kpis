"""
Download SQLite databases from GitHub-data releases for upstream reporting.

This script fetches the latest releases from:
- jupyter/github-data
- 2i2c-org/github-data

It saves the databases into book/_build/upstream-data/{jupyter,2i2c}.
"""

from pathlib import Path

import pooch
import requests


def download_repo_data(repo, data_dir):
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching latest release from {repo}...")
    response = requests.get(api_url)
    response.raise_for_status()

    release = response.json()
    assets = release.get("assets", [])
    db_assets = [asset for asset in assets if asset["name"].endswith(".db")]

    if not db_assets:
        raise RuntimeError(f"No .db files found in {repo} release assets.")

    print(f"Found {len(db_assets)} database file(s)")

    for asset in db_assets:
        filename = asset["name"]
        download_url = asset["browser_download_url"]

        pooch.retrieve(url=download_url, known_hash=None, path=data_dir, fname=filename)

        print(f"  Saved to {data_dir / filename}")


def main():
    here = Path(__file__).parent
    root_dir = here / "../_build/upstream-data"

    download_repo_data("jupyter/github-data", root_dir / "jupyter")
    print("")
    download_repo_data("2i2c-org/github-data", root_dir / "2i2c")

    print(f"\nDownload complete! Data saved to: {root_dir.resolve()}")


if __name__ == "__main__":
    main()
