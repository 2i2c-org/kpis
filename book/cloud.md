---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.17.2
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

# Cloud and hub usage

This displays the usage of our cloud infrastructure to give an understanding of our infrastructure setup and the communities that use it.

Last updated: **{sub-ref}`today`**

```{admonition} Data source
:class: dropdown

Raw data:

- {download}`data/maus-by-hub.csv`
- {download}`data/maus-unique-by-cluster.csv`.

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
from IPython.display import Markdown, display
import twoc

twoc.set_plotly_defaults()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

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
df = pd.read_csv("data/maus-by-hub.csv")

# Remove staging hubs and prometheus clusters since those aren't relevant to stats
df = df[~df.hub.str.contains("staging")]
df = df[~df.cluster.str.contains("prometheus")]

# Remove utoronto/highmem - this hub had a data collection bug from Feb 6 to Apr 2, 2025
# that was double-counting users from other hubs (see: https://github.com/2i2c-org/meta/issues/2818)
df = df[~((df.cluster == "utoronto") & (df.hub == "highmem"))]

# Drop rows with zero users (clusters that didn't exist yet)
df = df[df["users"] > 0]

# To make it easier to visualize these
df["clusterhub"] = df.apply(lambda a: f"{a['cluster']}/{a['hub']}", axis=1)

# Load unique users per cluster (deduplicated across hubs)
df_unique = pd.read_csv("data/maus-unique-by-cluster.csv")
df_unique["date"] = pd.to_datetime(df_unique["date"])

# Drop rows with zero users (clusters that didn't exist yet)
df_unique = df_unique[df_unique["unique_users"] > 0]
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Active users

Unique monthly active users for each cluster.
Clusters roughly map onto member communities (several of which have several sub-communities and hubs underneath them).

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
sorted_unique = df_unique.groupby("cluster")["unique_users"].mean().sort_values(ascending=False).index.values
fig = px.area(
    df_unique,
    x="date",
    y="unique_users",
    color="cluster",
    category_orders={"cluster": sorted_unique},
    title="Unique monthly users across all 2i2c clusters",
    labels={"unique_users": "users"},
    height=500,
)
# Add a button to toggle between linear and log y-axis
fig.update_layout(
    updatemenus=[
        dict(
            type="buttons",
            direction="left",
            x=0.0, y=1.15,
            buttons=[
                dict(label="Linear", method="relayout", args=[{"yaxis.type": "linear"}]),
                dict(label="Log", method="relayout", args=[{"yaxis.type": "log"}]),
            ],
        )
    ]
)
fig.show()
```

Click the dropdown for a list of month-end unique MAU counts, and see the dropdown at the top of the page for the raw data.

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
# Filter to month-end dates only for the summary table
df_month_end = df_unique[df_unique["date"].dt.is_month_end]

# Pivot so clusters are columns and dates are rows
table = df_month_end.pivot(index="date", columns="cluster", values="unique_users")
table.index = table.index.strftime("%Y-%m")
table = table.fillna(0).astype(int)
table["Total"] = table.sum(axis=1)
display(table)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Number of clusters and hubs we run

Multiple hubs are often run on a single cluster (e.g. a community with many sub-communities, one hub per class at an institution, etc).

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Number of hubs on each cluster over time
unique_hubs = df.groupby(["cluster", "date"]).nunique("clusterhub")["clusterhub"].to_frame("hubs").reset_index()
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
n_hubs = int(np.ceil(unique_hubs.query("date > @last_week").groupby("cluster")["hubs"].mean().sum()))
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
sorted_clusters = unique_hubs.groupby("cluster")["hubs"].max().sort_values(ascending=False).index.values

px.area(unique_hubs, x="date", y="hubs", color="cluster", title="Number of active hubs by cluster", category_orders={"cluster": sorted_clusters})
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Active users per hub

Active users broken down by each hub that we run.
Gives an idea of whether we have many hubs with few users, vs. a few hubs with a ton of users.

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

#### Count hubs by community size

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Mean users for each hub
df_sums = df.groupby("clusterhub")["users"].mean().reset_index()

# Calculate bins and add it to data for plotting 
bins = [0, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
labels = [f"{bins[ii]}-{bins[ii+1]}" for ii in range(len(bins)-1)]
df_sums["bin"] = pd.cut(df_sums["users"], bins, labels=labels, right=False)
max_y_bins = df_sums.groupby("bin").count()["users"].max() + 10
```

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

#### Number of hubs binned by size

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr, remove-stdout]
---
binned_data = df_sums.groupby("bin").size().reset_index(name="count")
fig_bins = px.bar(
    binned_data,
    x="bin",
    y="count",
    title="Number of hubs in bins of active users"
)
fig_bins.update_xaxes(title_text="Monthly Active Users", tickangle=-45)
fig_bins.update_yaxes(title_text="Number of hubs", range=[0, max_y_bins])
fig_bins.show()
```


