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

# Upstream community activity

This is a short visualization of the 2i2c team's activity in upstream repositories. Its goal is to give a high level indication of where we're spending our time in key upstream communities.

Last updated: **{sub-ref}`today`**

```{admonition} Work in progress!
This is a work in progress, so some of the GitHub search queries might be slightly off.
Use this to get a high-level view, but don't read too much into the details.
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
from github_activity import get_activity
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import os
from yaml import safe_load
from pathlib import Path
from subprocess import run
import json
from ast import literal_eval
from IPython.display import Markdown
from urllib.parse import quote
from tomlkit import parse
```

+++ {"tags": ["remove-cell"]}

## Load and prep data

```{code-cell} ipython3
:tags: [remove-cell]

# Load data that we'll use for visualization
with Path("data/key-communities.toml").open() as ff:
    communities = parse(ff.read())["communities"]
communities = list(filter(lambda a: a != "2i2c-org", communities))
team = safe_load(Path("data/team.yml").read_text())
```

```{code-cell} ipython3
:tags: [remove-cell]

# If data already exists locally, load it
path_data = Path("data/github-activity.csv")
if path_data.exists():
    DATETIME_COLUMNS = ["createdAt", "updatedAt", "closedAt"]
    data = pd.read_csv(path_data, parse_dates=DATETIME_COLUMNS)
else:
    print("No data found, please run `python scripts/download_github_data.py`")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Drop the 2i2c-org community because it's not upstream
data = data.query("org != '2i2c-org'")

# This is an "earliest date" we'll use to cut off visualization
earliest = data["updatedAt"].min()
latest = data["updatedAt"].max()

Markdown(f"Showing data from **{earliest:%Y-%m-%d}** to **{latest:%Y-%m-%d}**")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Pull out the comments into our own dataframe
new_comments = []
for _, row in data.iterrows():
    iicomments = pd.DataFrame(literal_eval(row["comments"]))
    if iicomments.shape[0] > 0:
        iicomments["author"] = iicomments["author"].map(lambda a: a["login"] if a is not None else None)
        iicomments.loc[:, ["org", "repo"]] = row[["org", "repo"]].tolist()
        new_comments.append(iicomments)
comments = pd.concat(new_comments)

# Only keep comments from our team members
comments = comments.query("author in @team")

for col in DATETIME_COLUMNS:
    if col in comments:
        comments[col] = pd.to_datetime(comments[col])

# Remove comments outside of this window
comments = comments.loc[comments["updatedAt"] > earliest]
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Helper functions for visualization
def visualize_by_org_repo(df, title="", number=25, kind="involves"):
    df_counts = df.groupby(["org", "repo"]).count().iloc[:, 0].sort_values(ascending=False)
    df_counts.name = "count"
    df_counts = df_counts.reset_index()
    df_counts = df_counts.head(number)
    df_counts["url"] = df_counts.apply(create_github_url, axis=1, kind=kind)
    
    ch = alt.Chart(df_counts, title=title).mark_bar().encode(
        x=alt.X("repo", sort=alt.SortField("count", "descending")),
        y="count",
        color="org",
        tooltip=["org", "repo", "count"],
        href="url",
    ).interactive()
    return ch

def create_github_url(row, kind="involves"):
    """Add a link to a GitHub query for each type of issue."""
    people = "+".join([f"{kind}%3A{person}" for person in team])
    query = f"repo%3A{row['org']}%2F{row['repo']}+{people}+updated%3A{earliest:%Y-%m-%d}..{latest:%Y-%m-%d}"
    url = f"https://github.com/search?q={query}"
    return url

def visualize_over_time(df, on="updatedAt", title=""):
    """Visualize activity binned by time."""
    df_time = (df
        .groupby(["org"])
        .resample("W", on=on)
        .count()
        .iloc[:, 0]
    )
    df_time.name = "count"
    df_time = df_time.reset_index()
    ch = alt.Chart(df_time, title=title, width=500).mark_bar(size=10).encode(
        x=on,
        y="count",
        color="org",
        tooltip=["org", "count"],
    ).interactive()
    return ch
```

## Key upstream communities

Key upstream communities are communities that 2i2c utilizes, empowers, and supports.
We try to use technology from these communities wherever possible, and put additional team resources towards making upstream contributions and providing general support.
See [the 2i2c team compass](inv:tc#open-source/key-communities) for more information about this.

Below are 2i2c's key upstream communities:

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
communities_list = "\n".join(f"- [{community}](https://github.com/{community})" for community in communities)
Markdown(f"Key upstream communities:\n\n{communities_list}")
```

## Merged PRs authored by team members

Pull Requests that were authored by a 2i2c team member, and merged by anyone.
This gives an idea of where we're committing code, documentation, and team policy improvements.

The plots below show recent activity over a 2-quarter window, while the button below runs a GitHub search for all activity since 2i2c's creation.

````{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# A GitHub search query for all merged PRs by 2i2c team members that
# were merged since 2i2c's creation.
pr_search_query = "+".join([f"author:{member}" for member in team])
pr_search_query = pr_search_query + "+" + "+".join([f"org:{org}" for org in communities])
pr_search_query = f"{pr_search_query}+is:pr+merged:>=2020-12-01"

pr_search_url = f"https://github.com/search?q={pr_search_query}"

Markdown(f"""\
```{{card}} All Merged PRs authored by 2i2c team members in key upstream communities
:link: {pr_search_url}

Click to see GitHub search
```
""")
````

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
authoredByUs = data.dropna(subset="closedAt").query("author in @team")
visualize_over_time(authoredByUs, on="closedAt", title="PRs authored by a team member that were merged, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
visualize_by_org_repo(authoredByUs, kind="mergedBy", title="PRs authored by a team member that were merged, by repository")
```

## PRs merged by team members

This gives an idea of which Pull Requests were **merged** by a team member (not necessarily authored). Merging Pull Requests is a reflection of reviewing and incorporating the work of _others_ as opposed to only our own work.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
mergedByUs = data.dropna(subset="closedAt").query("mergedBy in @team")
visualize_over_time(mergedByUs, on="closedAt", title="PRs merged by a team member, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
visualize_by_org_repo(mergedByUs, title="PRs merged by a team member, by repository")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Issues opened by team members

This shows issues that a 2i2c team member has opened over time.
This gives an idea of where we are noticing issues and suggesting improvements in upstream repositories.
The plots below show recent activity over a 2-quarter window, while the button below runs a GitHub search for all activity since 2i2c's creation.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# A GitHub search query for all opened issues by 2i2c team members
# since 2i2c's creation.
pr_search_query = "+".join([f"author:{member}" for member in team])
pr_search_query = pr_search_query + "+" + "+".join([f"org:{org}" for org in communities])
pr_search_query = f"{pr_search_query}+is:issue+created:>=2020-12-01"

pr_search_url = f"https://github.com/search?q={pr_search_query}"

Markdown(f"""\
:::{{card}} All Issues opened by 2i2c team members in key upstream communities.
:link: {pr_search_url}

Click to see GitHub search.

:::
""")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
issues = data.loc[["issues/" in ii for ii in data["url"].values]]
issuesByUs = issues.dropna(subset="createdAt").query("author in @team")
visualize_over_time(issuesByUs, on="updatedAt", title="Issues opened by a team member, over time")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Now we break it down by repository to visualize where this activity has been directed.

:::{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
:::

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
visualize_by_org_repo(issuesByUs, "Issues opened by a team member, by repository", kind="author")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Comments by a 2i2c team member

Comments are a reflection of where we're participating in conversations, discussions, brainstorming, guiding others, etc. They are a reflection of "overall activity" because comments tend to happen everywhere, and may not be associated with a specific change to the code.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
---
visualize_over_time(comments, title="Comments made by a team member, over time")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Now we break it down by repository to visualize where this activity has been directed.

:::{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
:::

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
visualize_by_org_repo(comments, kind="commenter", title="Comments by a team member, by repository.")
```
