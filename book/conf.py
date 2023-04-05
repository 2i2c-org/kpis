title = "2i2c KPIs"
extensions = ["myst_nb", "sphinx_design", "sphinx_togglebutton", "sphinx.ext.intersphinx"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]
only_build_toc_files = True

myst_enable_extensions = [
  "linkify",
]

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