title = "2i2c KPIs"
extensions = [
    "myst_nb",
    "sphinx_design",
    "sphinx_togglebutton",
    "sphinx.ext.intersphinx",
]

exclude_patterns = [
    "_build",
    "_build/data",
    "scripts/_build",
    "Thumbs.db",
    ".DS_Store",
    "**.ipynb_checkpoints",
    "data/**",
]
only_build_toc_files = True

myst_enable_extensions = [
    "linkify",
    "colon_fence",
]

nb_render_markdown_format = "myst"
nb_execution_raise_on_error = True
nb_execution_timeout = 180
nb_execution_excludepatterns = []

html_title = "2i2c KPIs"
html_theme = "sphinx_2i2c_theme"
html_static_path = ["_static"]

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

# Ensure key communities is downloaded
from subprocess import run

run(["python", "download_key_communities.py"], cwd="scripts", check=True)


def setup(app):
    # Load RequireJS for interactive visualizations
    # ref: https://jupyterbook.org/en/stable/interactive/interactive.html#plotly
    app.add_js_file(
        "https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js"
    )
