"""
Download key communities CSV file from team-compass repo.
"""

from pathlib import Path
import urllib.request

# URL of the file to download
file_url = "https://raw.githubusercontent.com/2i2c-org/team-compass/main/open-source/data/key-communities.toml"
file_local = Path("../data/key-communities.toml")

# Always download fresh data for consistency between local and CI builds
print(f"Downloading key communities file to: {file_local}")
with urllib.request.urlopen(file_url) as response:
    file_content = response.read()
    file_local.write_bytes(file_content)
print(f"Downloaded key communities file to: {file_local}")
