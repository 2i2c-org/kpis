---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.4
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

+++ {"editable": true, "slideshow": {"slide_type": ""}}

% CSS for the big numbers

<style>
.big-number .sd-card-text {
    font-size: 3rem;
}
</style>

# JupyterHub usage

This displays the usage of our cloud infrastructure to give an understanding of our infrastructure setup and the communities that use it.

Last updated: **{sub-ref}`today`**

```{admonition} Data source
:class: dropdown
This data is pulled from these two sources:

1. The list of our hubs and clusters is pulled from [our `infrastructure/` repository](https://github.com/2i2c-org/infrastructure/tree/master/config/clusters).
2. The active users data stream produced by JupyterHub and exposed at `metrics/`.
   [See this PR for the feature](https://github.com/jupyterhub/jupyterhub/pull/4214).
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import pandas as pd
import numpy as np
import datetime
from pathlib import Path
import plotly.express as px
import altair as alt
from textwrap import dedent
from IPython.display import Markdown, display
import requests
from rich.progress import track
from twoc import colors
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Load and munge data

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
today = pd.to_datetime("today")
last_week = today - datetime.timedelta(days=7)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Load the data
df = pd.read_csv("data/hub-activity.csv")

# Remove staging hubs since those aren't relevant to stats
df = df[~df.hub.str.contains("staging")]

# To make it easier to visualize these
df["clusterhub"] = df.apply(lambda a: f"{a['cluster']}/{a['hub']}", axis=1)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Number of hubs

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Number of hubs on each cluster over time
unique_hubs = df.query("timescale == 'monthly'").groupby(["cluster", "date"]).nunique("clusterhub")["clusterhub"].to_frame("hubs").reset_index()
unique_hubs["date"] = pd.to_datetime(unique_hubs["date"])
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# The latest number of unique hubs and clusters
n_hubs = int(np.ceil(unique_hubs.query("date > @last_week").groupby("cluster").mean("hubs")["hubs"].sum()))
n_clusters = unique_hubs.query("date > @last_week")["cluster"].nunique()
```

`````{code-cell} ipython3
---
editable: true
mystnb:
  markdown_format: myst
slideshow:
  slide_type: ''
tags: [remove-input]
---
Markdown(f"""
````{{grid}}
:class-container: big-number

```{{grid-item-card}} Total clusters
{n_clusters}
```
```{{grid-item-card}} Total hubs
{n_hubs}
```
````
""")
`````

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [full-width, remove-input]
---
# Sort the clusters by most to least hubs
sorted_clusters = unique_hubs.groupby("cluster").max("hubs").sort_values("hubs", ascending=False).index.values

px.area(unique_hubs, x="date", y="hubs", color="cluster", title="Number of active hubs by cluster", category_orders={"cluster": sorted_clusters})
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Geographic map of community locations

Below is a visualization that represents the hubs

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import pandas as pd
import pandas as pd
import plotly.express as px
import numpy as np
from plotly.express.colors import qualitative
import plotly.io as pio
pio.renderers.default = "notebook"
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Load the latest AirTable data
communities = pd.read_csv("./data/airtable-communities.csv")

# Clean up a bit
communities = communities.rename(columns={"domain (from Hubs)": "domain"})

# Drop communities that are missing location/hubs/domains from hubs
communities = communities.dropna(subset=["Location", "Hubs", "domain"])
for col in ["id", "domain", "Location"]:
    communities[col] = communities[col].map(lambda a: eval(a))
communities["Location"] = communities["Location"].map(lambda a: a[0])

# Calculate the number of users for each hub
for ix, irow in communities.iterrows():
    clusters = eval(irow["cluster"])
    hubs = irow["id"]
    clusterhub = [f"{a}/{b}" for a, b in zip(clusters, hubs)]

    # Grab the average number of monthly users for this community across all clusters/hubs
    hubs = df.query("clusterhub in @clusterhub and timescale == 'monthly'")
    # Average across time for each hub, and then add across all hubs
    hubs = df.query("clusterhub in @clusterhub and timescale == 'monthly'")
    n_users = hubs.groupby("clusterhub").mean("users")["users"].sum().round()
    communities.loc[ix, "users"] = n_users
```

```{code-cell} ipython3
---
tags: [remove-cell]
---
# Read in locations data and link it to our communities
locations = pd.read_csv("./data/airtable-locations.csv")
communities = pd.merge(communities, locations[["aid", "Latitude", "Longitude"]], left_on="Location", right_on="aid", how="left")

# Rename Lattitude and Longitude to be easier to work with
communities = communities.rename(columns={"Latitude": "lat", "Longitude": "lon"})
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Drop any records without users because these aren't valid
missing_records = communities["users"].isnull()
print(f"Dropping {missing_records.sum()} records with missing users...")
communities = communities.loc[~missing_records]

# Add a log-scaled column to ease plotting
communities["users_scaled"] = np.log10(communities["users"])

# Drop communities that have 0 users
communities = communities[communities["users_scaled"] != -np.inf]

# Add XY jitter so that overlapping hubs don't totally block each other
communities['lat_jitter'] = communities['lat'].map(lambda a: a + np.random.normal(0, 0.2))
communities['lon_jitter'] = communities['lon'].map(lambda a: a + np.random.normal(0, 0.2))
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
def update_geo_fig(fig):
    """Modify the style of a geo plot for 2i2c branding."""
    fig.update_geos(oceancolor=colors["paleblue"], landcolor="white", subunitcolor="grey", bgcolor='rgba(0,0,0,0)', showland=True, showocean=True)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
)

def update_png_fig(fig):
    """Update a plot for printing to a PNG."""
    # Set minimum marker size
    fig.update_traces(
        marker=dict(
            sizemin=10,
        )
    )
    # Remove margin on PNG exports
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
```

```{code-cell} ipython3
---
editable: true
raw_mimetype: ''
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
plotly_config = dict(
    lat="lat_jitter", lon="lon_jitter",
    hover_name="Community", hover_data={"users": True, "lat_jitter": False, "lon_jitter": False, "users_scaled": False, "Location": True},
    size="users_scaled", # size of markers, "pop" is one of the columns of gapminder
    color="Constellation",
    width=900, height=500,
    color_discrete_sequence=qualitative.D3,
)
fig = px.scatter_geo(communities, projection="natural earth", **plotly_config)
fig2 = px.scatter_geo(communities, projection="albers usa", **plotly_config)

for fig in [fig, fig2]:
    update_geo_fig(fig)
    fig.show()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Below is a dropdown with a few PNGs of different hub constellations for re-use.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, hide-output]
---
# This cell is for generating PNG images that can be re-used elsewhere.
# It will hide all the images under a dropdown so that it doesn't clutter the screen.
from pathlib import Path
plotly_config = dict(
    lat="lat_jitter", lon="lon_jitter",
    hover_name="Community", hover_data={"users": True, "lat_jitter": False, "lon_jitter": False, "users_scaled": False, "Location": True},
    size="users_scaled", # size of markers, "pop" is one of the columns of gapminder
    width=1500, height=800,
)
fig = px.scatter_geo(communities, projection="natural earth", color_discrete_sequence=["#e14e4f"], **plotly_config)

# Save our maps to the _static folder
path_maps = Path("_static/maps/")
path_maps.mkdir(parents=True, exist_ok=True)
path_file = path_maps / f"2i2c_hubs_map.png"
update_geo_fig(fig)
update_png_fig(fig)
fig.write_image(path_file)

# Output for the cell
display(Markdown(f"**All 2i2c hubs**"))
display(Markdown(f"Permanent link: {{download}}`2i2c.org/kpis{path_file} <{path_file}>`"))
update_geo_fig(fig)
fig.show("png")


for constellation, idata in communities.groupby("Constellation"):
    fig = px.scatter_geo(idata, projection="natural earth", color_discrete_sequence=["#e14e4f"],
                         title="", **plotly_config)
    path_file = f"_static/maps/{constellation}_map.png"
    display(Markdown(f"Constellation: **{constellation}**"))
    display(Markdown(f"Permanent link: {{download}}`2i2c.org/kpis{path_file} <{path_file}>`"))
    update_geo_fig(fig)
    update_png_fig(fig)
    fig.show("png")
    fig.write_image(path_file)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Active users

Average active users over the past 6 months.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Sum by cluster so we avoid having too many categories
df_clusters = df.groupby(["cluster", "date", "timescale"]).sum("users").reset_index()

# Add logusers
df_clusters = df_clusters.query("users > 0")
df_clusters["logusers"] = df_clusters["users"].map(np.log10)

# List of clusters sorted by size
sorted_clusters = df_clusters.groupby("cluster").mean("users").sort_values("users", ascending=False).index.values
```

`````{code-cell} ipython3
---
editable: true
mystnb:
  markdown_format: myst
slideshow:
  slide_type: ''
tags: [remove-input]
---
grid = """
````{grid}
:class-container: big-number
%s
````
"""
scale_ordering = ["daily", "monthly"]
interior = []
for scale in scale_ordering:
    users = df_clusters.query("timescale == @scale").groupby("cluster").mean("users")["users"].sum()
    interior.append(dedent("""\
    ```{grid-item-card} %s
    %s
    ```\
    """ % (f"{scale.capitalize()} users", int(users))))
Markdown(grid % "\n".join(interior))
`````

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Monthly active users over the past 6 months

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
for scale in ["monthly", "daily"]:
    for kind in ["users", "logusers"]:
        bar = px.area(
            df_clusters.query("timescale == @scale"),
            x="date",
            y=kind,
            color="cluster",
            category_orders={"cluster": sorted_clusters},
            line_group="cluster",
            title=f"{scale.capitalize()} {kind} across all 2i2c clusters",
            height=500
        )
        bar.show()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Active users by hub

Active users broken down by each hub that we run.
We break our hubs into two groups as some hubs have orders of magnitude more users than others.

+++ {"editable": true, "slideshow": {"slide_type": ""}}

#### Count hubs by community size

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Mean users for each hub
df_sums = df.groupby(["clusterhub", "timescale"]).mean("users")

# Calculate bins and add it to data for plotting 
bins = [0, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
labels = [f"{bins[ii]}-{bins[ii+1]}" for ii in range(len(bins)-1)]
df_sums["bin"] = pd.cut(df_sums["users"], bins, labels=labels, right=False)
df_sums = df_sums.reset_index()
max_y_bins = df_sums.groupby(["timescale", "bin"]).count()["users"].max() + 10
max_y_users = df_sums.groupby(["timescale", "bin"]).sum()["users"].max() + 100
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

#### Total number of users binned by community size

Tells us the percentage of our userbase that comes from different community sizes.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr, remove-stdout]
---
chs_bins = []
chs_users = []
chs_perc = []
groups = df_sums.groupby("timescale")
for scale in scale_ordering:
    idata = groups.get_group(scale).copy()
    binned_data = idata.groupby('bin').size().reset_index(name='count')

    # Number 
    ch = alt.Chart(idata, title=f"{scale}").mark_bar().encode(
        alt.X("bin:O", scale=alt.Scale(domain=labels), axis=alt.Axis(labelAngle=-45), title=f"{scale} Active Users"),
        y=alt.Y('count()', title="Number of communities", scale=alt.Scale(domain=[0, max_y_bins])),
        color="clusterhub",
        tooltip=["users", "clusterhub"],
    ).interactive()
    chs_bins.append(ch)

    # Percentage breakdown chart
    bin_sums = idata.groupby("bin").sum()["users"]
    bin_sums = bin_sums / bin_sums.sum()
    ch = alt.Chart(bin_sums.reset_index(), title=f"{scale}").mark_bar().encode(
        x = "bin",
        y = alt.Y("users", axis=alt.Axis(format='%'), scale=alt.Scale(domain=[0, 1])),
        tooltip=["bin", alt.Tooltip("users", format='.0%')],
    ).interactive()
    chs_perc.append(ch)

# Display the charts
display(alt.hconcat(*chs_bins, title=f"Number of communities in bins of active users"))
display(alt.hconcat(*chs_users, title=f"Total Active Users by community size"))
display(alt.hconcat(*chs_perc, title=f"% {scale} Total Active Users by community size"))
```

```{code-cell} ipython3

```
