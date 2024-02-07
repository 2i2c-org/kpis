title = "2i2c KPIs"
extensions = ["myst_nb", "sphinx_design", "sphinx_togglebutton", "sphinx.ext.intersphinx"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints", "data/**"]
only_build_toc_files = True

myst_enable_extensions = [
  "linkify",
  "colon_fence",
]

nb_render_markdown_format = "myst"

html_title = "2i2c KPIs"
html_theme = "sphinx_2i2c_theme"

html_theme_options = {
   "navbar_align": "left",
   "repository_url": "https://github.com/2i2c-org/kpis",
   "use_repository_button": True,
}

intersphinx_mapping = {
    "docs": ("https://docs.2i2c.org/en/latest/", None),
    "infra": ("https://infrastructure.2i2c.org/en/latest/", None),
    "tc": ("https://compass.2i2c.org/en/latest/", None),
}

# Download key communities CSV file if it isn't there
from pathlib import Path
import urllib.request

# URL of the file to download
file_url = 'https://compass.2i2c.org/_downloads/8fa10f7f661246ec4fbe1515e254aa6d/key-communities.toml'
file_local = Path("data/key-communities.toml")

# Open the URL
if not file_local.exists():
    with urllib.request.urlopen(file_url) as response:
        # Read the content of the response
        file_content = response.read()
        file_local.write_bytes(file_content)
        print(f"Downloaded new key communities file to: {file_local}")
