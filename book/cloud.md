---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.1
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
from pathlib import Path
import altair as alt
from textwrap import dedent
from IPython.display import Markdown, display
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
# Load the data
df = pd.read_csv("data/hub-activity.csv", index_col=0)

# Remove the staging hubs since they are generally redundant
df = df.loc[df["hub"].map(lambda a: "staging" not in a)]

# Categorize hub type
df = df.replace({"basehub": "Basic", "daskhub": "Dask Gateway"})
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Number of hubs

`````{code-cell} ipython3
---
editable: true
mystnb:
  markdown_format: myst
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Basic stats about our number of hubs and clusters
n_clusters = df["cluster"].nunique()
n_hubs = df["hub"].nunique()

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

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Number of hubs per cluster

_excluding staging hubs_

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
table_nhubs = df.groupby("cluster").agg({"hub": "nunique"}).sort_values("hub", ascending=False)
table_nhubs.columns = ["Number of hubs"]
table_nhubs.T
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Types of hubs

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
hub_types = df.query("scale == 'Weekly'").groupby("chart").agg({"hub": "count", "users": "sum"})
hub_types = hub_types.rename(columns={"hub": "Number of hubs", "users": "Weekly users"})
hub_types.index.name = "Chart type"
hub_types
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Active users

### Total active users

Total active users across all of our hubs and communities.

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
scale_ordering = ["Monthly", "Weekly", "Daily"]
interior = []
for scale in scale_ordering:
    users = df.query("scale==@scale")["users"].sum()
    interior.append(dedent("""\
    ```{grid-item-card} %s
    %s
    ```\
    """ % (scale, users)))
Markdown(grid % "\n".join(interior))
`````

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
# Calculate bins and add it to data for plotting 
bins = [0, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
labels = [f"{bins[ii]}-{bins[ii+1]}" for ii in range(len(bins)-1)]
df["bin"] = pd.cut(df["users"], bins, labels=labels, right=False)
max_y_bins = df.groupby(["scale", "bin"]).count()["users"].max() + 10
max_y_users = df.groupby(["scale", "bin"]).sum()["users"].max() + 100
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
groups = df.groupby("scale")
for scale in scale_ordering:
    idata = groups.get_group(scale).copy()
    binned_data = idata.groupby('bin').size().reset_index(name='count')

    # Number 
    ch = alt.Chart(idata, title=f"{scale}").mark_bar().encode(
        alt.X("bin:O", scale=alt.Scale(domain=labels), axis=alt.Axis(labelAngle=-45), title=f"{scale} Active Users"),
        y=alt.Y('count()', title="Number of communities", scale=alt.Scale(domain=[0, max_y_bins])),
        color="cluster",
        tooltip=["users", "hub"],
    ).interactive()
    chs_bins.append(ch)

    # CHART: Number of total users grouped by community size
    ch = alt.Chart(idata, title=f"{scale}").mark_bar().encode(
        alt.X("bin:O", scale=alt.Scale(domain=labels), axis=alt.Axis(labelAngle=-45), title=f"{scale} Active Users"),
        y=alt.Y('users', title="Number of users", scale=alt.Scale(domain=[0, max_y_users])),
        color="cluster",
        tooltip=["users", "hub"],
    ).interactive()
    chs_users.append(ch)

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
---
editable: true
slideshow:
  slide_type: ''
---

```
