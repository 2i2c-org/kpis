---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.4
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

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
tags: [remove-cell]
---

import pandas as pd
from pathlib import Path
import altair as alt
from textwrap import dedent
from IPython.display import Markdown
```

## Load and munge data

```{code-cell} ipython3
---
tags: [remove-cell]
---
# Load the data
df = pd.read_csv("data/hub-activity.csv", index_col=0)

# Remove the staging hubs since they are generally redundant
df = df.loc[df["hub"].map(lambda a: "staging" not in a)]
```

## Number of hubs

`````{code-cell} ipython3
---
tags: [remove-input]
mystnb:
  markdown_format: myst
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

### Number of hubs per cluster

_excluding staging hubs_

```{code-cell} ipython3
---
tags: [remove-input]
---
table_nhubs = df.groupby("cluster").agg({"hub": "nunique"}).sort_values("hub", ascending=False)
table_nhubs.columns = ["Number of hubs"]
table_nhubs.T
```

## Active users

### Total active users

Total active users across all of our hubs and communities.

`````{code-cell} ipython3
---
tags: [remove-input]
mystnb:
  markdown_format: myst
---
grid = """
````{grid}
:class-container: big-number
%s
````
"""
scale_ordering = ["Daily", "Weekly", "Monthly"]
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

### Active users by hub

Active users broken down by each hub that we run.

```{code-cell} ipython3
---
tags: [remove-input, remove-stderr, remove-stdout]
---
chs = []
groups = df.query("cluster!='utoronto'").groupby("scale")
for scale in scale_ordering:
    idata = groups.get_group(scale)
    ch = alt.Chart(idata, title=f"{scale} users").mark_bar().encode(
        alt.X("users:Q", bin=True),
        y='count()',
        color="scale",
        tooltip=["users", "hub"],
    ).interactive()
    chs.append(ch)
alt.hconcat(*chs)
```

### Outlier hubs

Table statistics for a few hand-picked outliers so they don't skew the data above.

```{code-cell} ipython3
---
tags: [remove-input]
---
dftable = df.query("cluster=='utoronto'")[["hub", "scale", "users"]].sort_values("scale", key=lambda col: col.map(lambda a: scale_ordering.index(a)))
dftable = dftable.set_index(["hub", "scale"]).unstack("scale")["users"][scale_ordering]
dftable.columns.name = None
dftable.style.set_caption("Usage data for outlier hub")
```
