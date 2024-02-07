"""
Download key communities CSV file if it isn't there
"""
from pathlib import Path
import urllib.request

# URL of the file to download
file_url = 'https://compass.2i2c.org/_downloads/8fa10f7f661246ec4fbe1515e254aa6d/key-communities.toml'
file_local = Path("../data/key-communities.toml")

# Open the URL
if not file_local.exists():
    with urllib.request.urlopen(file_url) as response:
        # Read the content of the response
        file_content = response.read()
        file_local.write_bytes(file_content)
        print(f"Downloaded new key communities file to: {file_local}")
else:
    print(f"Key communities file already exists at: {file_local}, skipping download...")