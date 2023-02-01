---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.1
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
mystnb:
  remove_code_source: true
  output_stderr: remove
---

# Upstream community activity

This is a short visualization of the 2i2c team's activity in upstream repositories. Its goal is to give a high level indication of where we're spending our time in key upstream communities.

```{admonition} Work in progress!
This is a work in progress, so some of the GitHub search queries might be slightly off.
Use this to get a high-level view, but don't read too much into the details.
```

```{code-cell} ipython3
:tags: [remove-cell]

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
```

+++ {"tags": ["remove-cell"]}

## Load and prep data

```{code-cell} ipython3
:tags: [remove-cell]

# Load data that we'll use for visualization
communities = safe_load(Path("data/key-communities.yml").read_text())
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
    print("No data found, please run `python ../scripts/download_github_data.py`")
```

```{code-cell} ipython3
# Drop the 2i2c-org community because it's not upstream
data = data.query("org != '2i2c-org'")

# This is an "earliest date" we'll use to cut off visualization
earliest = data["updatedAt"].min()
latest = data["updatedAt"].max()

Markdown(f"Showing data from **{earliest:%Y-%m-%d}** to **{latest:%Y-%m-%d}**")
```

```{code-cell} ipython3
:tags: [remove-cell]

# Pull out the comments into our own dataframe
new_comments = []
for _, row in data.iterrows():
    iicomments = pd.DataFrame(literal_eval(row["comments"]))
    if iicomments.shape[0] > 0:
        iicomments["author"] = iicomments["author"].map(lambda a: a["login"] if a is not None else None)
        iicomments[["org", "repo"]] = row[["org", "repo"]]
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
:tags: [remove-cell]

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

## Comments by a 2i2c team member

Comments are a reflection of where we're participating in conversations, discussions, brainstorming, guiding others, etc. They are a reflection of "overall activity" because comments tend to happen everywhere, and may not be associated with a specific change to the code.

```{code-cell} ipython3
visualize_over_time(comments.query("author in @team"), title="Comments made by a team member, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
visualize_by_org_repo(comments, kind="commenter", title="Comments by a team member, by repository.")
```

+++ {"tags": []}

## Issues opened by team members

This shows issues that a 2i2c team member has opened over time.
This gives an idea of where we are noticing issues and suggesting improvements in upstream repositories.

```{code-cell} ipython3
issues = data.loc[["issues/" in ii for ii in data["url"].values]]
issuesByUs = issues.dropna(subset="createdAt").query("author in @team")
visualize_over_time(issuesByUs,on="closedAt", title="Issues opened by a team member, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
visualize_by_org_repo(issuesByUs, "Issues opened by a team member, by repository", kind="author")
```

+++ {"tags": []}

## Merged PRs authored by team members

Pull Requests that were authored by a 2i2c team member, and merged by anyone.
This gives an idea of where we're committing code, documentation, and team policy improvements.

```{code-cell} ipython3
authoredByUs = data.dropna(subset="closedAt").query("author in @team")
visualize_over_time(authoredByUs, on="closedAt", title="PRs authored by a team member that were merged, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
visualize_by_org_repo(authoredByUs, kind="mergedBy", title="PRs authored by a team member that were merged, by repository")
```

## PRs merged by team members

This gives an idea of which Pull Requests were **merged** by a team member (not necessarily authored). Merging Pull Requests is a reflection of reviewing and incorporating the work of _others_ as opposed to only our own work.

```{code-cell} ipython3
mergedByUs = data.dropna(subset="closedAt").query("mergedBy in @team")
visualize_over_time(mergedByUs, on="closedAt", title="PRs merged by a team member, over time")
```

Now we break it down by repository to visualize where this activity has been directed.

```{tip}
Click a bar to show a GitHub search that roughly corresponds to the underlying data.
```

```{code-cell} ipython3
visualize_by_org_repo(mergedByUs, title="PRs merged by a team member, by repository")
```
