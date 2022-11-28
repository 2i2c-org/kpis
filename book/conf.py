title = "2i2c KPIs"
extensions = ["myst_nb", "sphinx_design", "sphinx_togglebutton"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]
only_build_toc_files = True

html_title = "2i2c KPIs"
html_theme = "sphinx_2i2c_theme"

html_theme_options = {
   "navbar_align": "left",
   "repository_url": "https://github.com/2i2c-org/kpis",
   "use_repository_button": True,
}
