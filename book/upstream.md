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

This page summarizes where 2i2c spends its time in the Jupyter ecosystem and in our own technical repositories.
It's goal is to give us an idea for where we're shouldering maintenance and development burden and having impact.

Last updated: **{sub-ref}`today`**

::::{dropdown} LFX Insights dashboards
[LFX Insights](https://insights.linuxfoundation.org/) is a service from the Linux Foundation to track community health and contributions.

:::{dropdown} JupyterHub
<iframe
    src="https://insights.linuxfoundation.org/embed/project/jupyterhub?widget=organizations-leaderboard&startDate=2025-01-23&endDate=2026-01-23&timeRangeKey=past365days&metric=all%3Aall&includeCollaborations=false"
    width="600"
    height="674"
    allowfullscreen
    loading="lazy"
    style="border: none; border-radius: 8px">
</iframe>

[source](https://insights.linuxfoundation.org/project/jupyterhub/contributors)
:::

:::{dropdown} Jupyter Book
<iframe
    src="https://insights.linuxfoundation.org/embed/project/jupyter-book?widget=organizations-leaderboard&startDate=2025-01-23&endDate=2026-01-23&timeRangeKey=past365days&metric=all%3Aall&includeCollaborations=false"
    width="600"
    height="674"
    allowfullscreen
    loading="lazy"
    style="border: none; border-radius: 8px">
</iframe>

[source](https://insights.linuxfoundation.org/project/jupyter-book/contributors)
:::
:::{dropdown} Jupyter Organization
<iframe
    src="https://insights.linuxfoundation.org/embed/project/jupyter?widget=organizations-leaderboard&startDate=2025-01-23&endDate=2026-01-23&timeRangeKey=past365days&metric=all%3Aall&includeCollaborations=false"
    width="600"
    height="674"
    allowfullscreen
    loading="lazy"
    style="border: none; border-radius: 8px">
</iframe>

[source](https://insights.linuxfoundation.org/project/jupyter/contributors)
:::
::::

```{code-cell} ipython3
---
tags: [remove-cell]
---
from pathlib import Path
import sqlite3
from subprocess import run

import altair as alt
import pandas as pd
from IPython.display import HTML, Markdown, display
from twoc import colors as twoc_colors
from yaml import safe_load

# Use HTML renderer so MyST renders charts without vega-lite mime warnings.
alt.renderers.enable("html")
alt.data_transformers.disable_max_rows()

# Colors we'll re-use
TWOC_PALETTE = [
    twoc_colors["bigblue"],
    twoc_colors["coral"],
    twoc_colors["lightgreen"],
    twoc_colors["magenta"],
    twoc_colors["yellow"],
    twoc_colors["forest"],
    twoc_colors["mauve"],
    twoc_colors["midnight"],
    twoc_colors["pink"],
]
```

```{code-cell} ipython3
---
tags: [remove-cell]
---
def load_activity_from_db(db_path, start_date_str, team_logins):
    conn = sqlite3.connect(db_path)
    users = pd.read_sql("SELECT id as user_id, login FROM users", conn)
    repos = pd.read_sql("SELECT id as repo_id, full_name FROM repos", conn)
    users["user_id"] = users["user_id"].astype("Int64")

    prs = pd.read_sql(
        """
        SELECT
            id as pr_id,
            user as user_id,
            merged_at,
            repo as repo_id,
            number,
            title
        FROM pull_requests
        WHERE merged_at >= ?
        """,
        conn,
        params=[start_date_str],
    )

    issues = pd.read_sql(
        """
        SELECT
            id as issue_id,
            user as issue_user_id,
            created_at,
            repo as repo_id,
            pull_request,
            number,
            title
        FROM issues
        WHERE created_at >= ?
        """,
        conn,
        params=[start_date_str],
    )

    comments = pd.read_sql(
        """
        SELECT
            ic.id as comment_id,
            ic.user as comment_user_id,
            ic.created_at as comment_created_at,
            i.user as issue_user_id,
            i.repo as repo_id
        FROM issue_comments ic
        JOIN issues i ON ic.issue = i.id
        WHERE ic.created_at >= ?
        """,
        conn,
        params=[start_date_str],
    )
    conn.close()

    prs = prs.merge(users, on="user_id", how="left")
    prs = prs.merge(repos, on="repo_id", how="left")
    prs = prs.rename(
        columns={"login": "author_login", "full_name": "repo_full_name"}
    )

    users_comment = users.rename(
        columns={"user_id": "comment_user_id", "login": "comment_author"}
    )
    users_issue = users.rename(
        columns={"user_id": "issue_user_id", "login": "issue_author"}
    )

    comments = comments.merge(users_comment, on="comment_user_id", how="left")
    comments = comments.merge(users_issue, on="issue_user_id", how="left")
    comments = comments.merge(repos, on="repo_id", how="left")
    comments = comments.rename(columns={"full_name": "repo_full_name"})

    issues = issues.merge(
        users.rename(columns={"user_id": "issue_user_id", "login": "issue_author"}),
        on="issue_user_id",
        how="left",
    )
    issues = issues.merge(repos, on="repo_id", how="left")
    issues = issues.rename(columns={"full_name": "repo_full_name"})
    issues = issues[issues["pull_request"].isna()]

    for df in (prs, comments, issues):
        repo_split = df["repo_full_name"].str.split("/", n=1, expand=True)
        df["org"] = repo_split[0]
        df["repo_url"] = "https://github.com/" + df["repo_full_name"].astype(str)

    prs["merged_at"] = pd.to_datetime(prs["merged_at"], utc=True, errors="coerce")
    comments["comment_created_at"] = pd.to_datetime(
        comments["comment_created_at"], utc=True, errors="coerce"
    )
    issues["created_at"] = pd.to_datetime(
        issues["created_at"], utc=True, errors="coerce"
    )

    prs["is_team"] = prs["author_login"].isin(team_logins)
    comments["is_team_comment"] = comments["comment_author"].isin(team_logins)
    comments["is_team_issue_author"] = comments["issue_author"].isin(team_logins)
    issues["is_team_issue_author"] = issues["issue_author"].isin(team_logins)

    return prs, comments, issues


def load_activity(db_paths, start_date_str, team_logins):
    prs_list = []
    comments_list = []
    issues_list = []
    for db_path in db_paths:
        prs, comments, issues = load_activity_from_db(
            db_path, start_date_str, team_logins
        )
        prs_list.append(prs)
        comments_list.append(comments)
        issues_list.append(issues)

    prs = pd.concat(prs_list, ignore_index=True) if prs_list else pd.DataFrame()
    comments = (
        pd.concat(comments_list, ignore_index=True) if comments_list else pd.DataFrame()
    )
    issues = pd.concat(issues_list, ignore_index=True) if issues_list else pd.DataFrame()
    return prs, comments, issues


def ensure_upstream_data(data_root):
    data_root.mkdir(parents=True, exist_ok=True)
    jupyter_dir = data_root / "jupyter"
    team_dir = data_root / "2i2c"

    run(["python", "scripts/download_upstream_data.py"], check=True)
    jupyter_db_paths = sorted(jupyter_dir.glob("*.db"))
    team_db_paths = sorted(team_dir.glob("*.db"))

    return jupyter_db_paths, team_db_paths
```

```{code-cell} ipython3
---
tags: [remove-cell]
---
team_logins = safe_load(Path("data/team.yml").read_text())

today = pd.Timestamp.utcnow().normalize()
start_year = today - pd.DateOffset(years=1)
start_recent = today - pd.DateOffset(months=2)
start_year_str = start_year.strftime("%Y-%m-%dT%H:%M:%SZ")

data_root = Path("_build/upstream-data")
jupyter_db_paths, team_db_paths = ensure_upstream_data(data_root)

prs_jupyter, comments_jupyter, issues_jupyter = load_activity(
    jupyter_db_paths, start_year_str, team_logins
)
team_prs, team_comments, _ = load_activity(team_db_paths, start_year_str, team_logins)

Markdown(
    f"Showing activity from **{start_year:%Y-%m-%d}** "
    f"to **{today:%Y-%m-%d}** (rolling 12 months)"
)
```

:::{dropdown} Data sources
These plots use SQLite releases from
[`jupyter/github-data`](https://github.com/jupyter/github-data) and
[`2i2c-org/github-data`](https://github.com/2i2c-org/github-data).
To refresh the local data:

- `python scripts/download_upstream_data.py`
:::


## Jupyter ecosystem

Key upstream communities are documented in the
[2i2c team compass](inv:tc#open-source/key-communities). We focus on Jupyter
here because `jupyter/github-data` provides consistent activity data we can
use for these projects.

```{code-cell} ipython3
---
tags: [remove-cell]
---
prs_upstream = prs_jupyter.copy()
comments_upstream = comments_jupyter.copy()
issues_upstream = issues_jupyter.copy()

prs_upstream_team = prs_upstream[prs_upstream["is_team"]]
issues_upstream_team = issues_upstream[issues_upstream["is_team_issue_author"]]
comments_upstream_team = comments_upstream[comments_upstream["is_team_comment"]]

upstream_top_repos = (
    prs_upstream_team.groupby(["org", "repo_full_name"])
    .size()
    .reset_index(name="merged_prs")
    .sort_values("merged_prs", ascending=False)
    .head(25)
)
upstream_top_repos["repo_url"] = (
    "https://github.com/" + upstream_top_repos["repo_full_name"].astype(str)
)

upstream_org_monthly = (
    prs_upstream_team.dropna(subset=["merged_at", "org"])
    .assign(month=lambda df: df["merged_at"].dt.to_period("M").dt.to_timestamp())
    .groupby(["month", "org"])
    .size()
    .reset_index(name="merged_prs")
)
upstream_org_totals = (
    upstream_org_monthly.groupby("month")["merged_prs"].sum().rename("month_total")
)
upstream_org_monthly = upstream_org_monthly.merge(
    upstream_org_totals, on="month", how="left"
)
upstream_org_monthly["share"] = (
    upstream_org_monthly["merged_prs"] / upstream_org_monthly["month_total"]
)
upstream_org_order = (
    upstream_org_monthly.groupby("org")["merged_prs"]
    .mean()
    .sort_values(ascending=False)
    .index.tolist()
)
upstream_org_monthly["org_rank"] = upstream_org_monthly["org"].map(
    {org: rank for rank, org in enumerate(upstream_org_order, start=1)}
)

upstream_comment_share = comments_upstream_team.copy()
upstream_comment_share["month"] = (
    upstream_comment_share["comment_created_at"].dt.to_period("M").dt.to_timestamp()
)
upstream_comment_share = (
    upstream_comment_share.groupby("month")
    .agg(
        total_comments=("comment_id", "count"),
        non_team_comments=("is_team_issue_author", lambda x: (~x).sum()),
    )
    .reset_index()
)
upstream_comment_share["non_team_share"] = (
    upstream_comment_share["non_team_comments"]
    / upstream_comment_share["total_comments"]
)


def build_color_maps(activity_df, orgs=None):
    if activity_df.empty:
        return {}, {}

    base_colors = TWOC_PALETTE
    orgs = sorted(activity_df["org"].dropna().unique()) if orgs is None else list(orgs)

    org_color_map = {}
    repo_color_map = {}
    for idx, org in enumerate(orgs):
        base_color = base_colors[idx % len(base_colors)]
        org_color_map[org] = base_color
        repos = (
            activity_df.loc[activity_df["org"] == org, "repo_full_name"]
            .dropna()
            .unique()
        )
        for repo in repos:
            repo_color_map[repo] = base_color

    return org_color_map, repo_color_map


def category_color_map(categories, palette):
    unique = list(dict.fromkeys(categories))
    return {name: palette[idx % len(palette)] for idx, name in enumerate(unique)}


upstream_activity_events = (
    pd.concat(
        [
            prs_upstream_team[["org", "repo_full_name"]],
            issues_upstream_team[["org", "repo_full_name"]],
            comments_upstream_team[["org", "repo_full_name"]],
        ],
        ignore_index=True,
    )
    .dropna()
)
upstream_org_color_map, upstream_repo_color_map = build_color_maps(
    upstream_activity_events
)


def prepare_repo_stack(df, date_col, top_n=12):
    df = df.dropna(subset=[date_col, "repo_full_name"]).copy()
    df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()
    totals = (
        df.groupby("repo_full_name")
        .size()
        .sort_values(ascending=False)
        .head(top_n)
    )
    df = df[df["repo_full_name"].isin(totals.index)]
    counts = (
        df.groupby(["month", "repo_full_name", "repo_url"])
        .size()
        .reset_index(name="count")
    )
    repo_order = (
        counts.groupby("repo_full_name")["count"]
        .mean()
        .sort_values(ascending=False)
    )
    counts["repo_rank"] = counts["repo_full_name"].map(
        {repo: rank for rank, repo in enumerate(repo_order.index, start=1)}
    )
    return counts, list(repo_order.index)


def stacked_repo_chart(df, repo_order, repo_color_map, title):
    color_range = [repo_color_map.get(repo, "#b0b0b0") for repo in repo_order]
    chart = (
        alt.Chart(df, title=title, height=300)
        .mark_bar(size=14, stroke="white", strokeWidth=0.6)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color(
                "repo_full_name:N",
                sort=repo_order,
                title="Repository",
                scale=alt.Scale(domain=repo_order, range=color_range),
            ),
            order=alt.Order("repo_rank:Q", sort="ascending"),
            tooltip=["month:T", "repo_full_name:N", "count:Q"],
            href="repo_url:N",
        )
    )
    return chart.properties(width="container").interactive()


upstream_prs_authored_stack, upstream_prs_authored_order = prepare_repo_stack(
    prs_upstream_team, "merged_at", top_n=12
)
upstream_issues_opened_stack, upstream_issues_opened_order = prepare_repo_stack(
    issues_upstream_team, "created_at", top_n=12
)
upstream_comments_stack, upstream_comments_order = prepare_repo_stack(
    comments_upstream_team, "comment_created_at", top_n=12
)
```

### Where our merged work lands (last 12 months)

This shows the repos where 2i2c team members merged the most PRs in upstream projects.

```{code-cell} ipython3
---
tags: [remove-input]
---
upstream_top_repos_clean = upstream_top_repos.dropna(
    subset=["repo_full_name", "repo_url"]
).copy()
upstream_top_repos_clean["merged_prs"] = pd.to_numeric(
    upstream_top_repos_clean["merged_prs"], errors="coerce"
)
upstream_top_repos_clean = upstream_top_repos_clean.dropna(subset=["merged_prs"])
upstream_top_org_order = list(
    dict.fromkeys(upstream_top_repos_clean["org"].dropna().tolist())
)
upstream_top_org_colors = [
    upstream_org_color_map.get(org, "#b0b0b0") for org in upstream_top_org_order
]

# A tiny, empty chart to force-load the JS libraries
empty = alt.Chart(pd.DataFrame()).mark_point()
empty.properties(
    title=""  # Forces the title to be an empty string instead of None
)
empty.display()

display(
    alt.Chart(upstream_top_repos_clean, height=350)
    .mark_bar(size=14)
    .encode(
        y=alt.Y("repo_full_name:N", sort="-x", title="Repository"),
        x=alt.X("merged_prs:Q", title="Merged PRs (team)"),
        color=alt.Color(
            "org:N",
            title="Org",
            scale=alt.Scale(domain=upstream_top_org_order, range=upstream_top_org_colors),
        ),
        tooltip=["org", "repo_full_name", "merged_prs"],
        href="repo_url:N",
    )
    .properties(width="container")
    .interactive()
)
```

### Share of merged PRs by org (last 12 months)

Monthly share of merged PRs authored by a team member across Jupyter orgs.

```{code-cell} ipython3
---
tags: [remove-input]
---
upstream_org_colors = [
    upstream_org_color_map.get(org, "#b0b0b0") for org in upstream_org_order
]

alt.Chart(upstream_org_monthly, height=260).mark_bar(
    size=14, stroke="white", strokeWidth=0.6
).encode(
    x=alt.X("month:T", title="Month"),
    y=alt.Y(
        "share:Q",
        title="Share of team merged PRs",
        axis=alt.Axis(format="%"),
    ),
    color=alt.Color(
        "org:N",
        scale=alt.Scale(domain=upstream_org_order, range=upstream_org_colors),
        title="Org",
    ),
    order=alt.Order("org_rank:Q"),
    tooltip=[
        "month:T",
        "org:N",
        "merged_prs:Q",
        alt.Tooltip("share:Q", format=".1%"),
    ],
).properties(width="container").interactive()
```

### Support to non-team authors over time

Monthly share of team comments that are on issues/PRs opened by non-team authors.

```{code-cell} ipython3
---
tags: [remove-input]
---
alt.Chart(upstream_comment_share, height=250).mark_line(point=True).encode(
    x=alt.X("month:T", title="Month"),
    y=alt.Y("non_team_share:Q", title="Share of comments on non-team items", axis=alt.Axis(format="%")),
    tooltip=[
        "month:T",
        alt.Tooltip("non_team_share:Q", format=".1%"),
        "total_comments:Q",
        "non_team_comments:Q",
    ],
).properties(width="container").interactive()
```

### Upstream activity by repository (stacked, last 12 months)

These stacked bars show monthly activity by repository. Hover for details,
and click a segment to open the repository.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_repo_chart(
    upstream_prs_authored_stack,
    upstream_prs_authored_order,
    upstream_repo_color_map,
    "Merged PRs authored by a team member, by repo",
)
```

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_repo_chart(
    upstream_issues_opened_stack,
    upstream_issues_opened_order,
    upstream_repo_color_map,
    "Issues opened by a team member, by repo",
)
```

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_repo_chart(
    upstream_comments_stack,
    upstream_comments_order,
    upstream_repo_color_map,
    "Comments made by a team member, by repo",
)
```

## 2i2c organization focus

Where we are spending time inside the 2i2c GitHub organization repositories.

```{code-cell} ipython3
---
tags: [remove-cell]
---
team_org_prs = team_prs[team_prs["is_team"]]
team_org_comments = team_comments[team_comments["is_team_comment"]]
team_repo_exclude = {"2i2c-org/2i2c-org.github.io", "2i2c-org/team-compass"}
team_org_prs = team_org_prs[~team_org_prs["repo_full_name"].isin(team_repo_exclude)]
team_org_comments = team_org_comments[
    ~team_org_comments["repo_full_name"].isin(team_repo_exclude)
]

team_total_prs = (
    team_org_prs.groupby("repo_full_name")
    .size()
    .rename("merged_prs")
    .reset_index()
    .sort_values("merged_prs", ascending=False)
    .head(20)
)
team_total_prs["repo_url"] = (
    "https://github.com/" + team_total_prs["repo_full_name"].astype(str)
)

team_activity_events = pd.concat(
    [
        team_org_prs.assign(activity_date=team_org_prs["merged_at"]),
        team_org_comments.assign(activity_date=team_org_comments["comment_created_at"]),
    ],
    ignore_index=True,
)
team_activity_events["month"] = (
    team_activity_events["activity_date"].dt.to_period("M").dt.to_timestamp()
)
team_repo_totals = (
    team_activity_events.groupby("repo_full_name")
    .size()
    .sort_values(ascending=False)
    .head(8)
)
team_repo_monthly = team_activity_events[
    team_activity_events["repo_full_name"].isin(team_repo_totals.index)
]
team_repo_monthly = (
    team_repo_monthly.groupby(["month", "repo_full_name"])
    .size()
    .reset_index(name="total_activity")
)
team_repo_monthly = team_repo_monthly.merge(
    team_repo_monthly.groupby("month")["total_activity"]
    .sum()
    .rename("month_total"),
    on="month",
    how="left",
)
team_repo_monthly["share"] = (
    team_repo_monthly["total_activity"] / team_repo_monthly["month_total"]
)
```

### Where we are focusing in our org (last 12 months)

Repos where the team merged the most PRs inside 2i2c-org.

```{code-cell} ipython3
---
tags: [remove-input]
---
team_repo_order = team_total_prs["repo_full_name"].tolist()
team_repo_color_map = category_color_map(team_repo_order, TWOC_PALETTE)
team_repo_colors = [team_repo_color_map.get(repo, "#b0b0b0") for repo in team_repo_order]

alt.Chart(team_total_prs, height=350).mark_bar(size=14).encode(
    y=alt.Y("repo_full_name:N", sort="-x", title="Repository"),
    x=alt.X("merged_prs:Q", title="Merged PRs (team)"),
    color=alt.Color(
        "repo_full_name:N",
        sort=team_repo_order,
        scale=alt.Scale(domain=team_repo_order, range=team_repo_colors),
        legend=None,
    ),
    tooltip=["repo_full_name", "merged_prs"],
    href="repo_url:N",
).properties(width="container").interactive()
```

### Team activity by repo over time (last 12 months)

Monthly share of team activity (PRs + comments) in the top 2i2c repos.

```{code-cell} ipython3
---
tags: [remove-input]
---
team_repo_monthly = team_repo_monthly.merge(
    team_total_prs[["repo_full_name", "repo_url"]],
    on="repo_full_name",
    how="left",
)
team_repo_monthly_order = team_repo_totals.index.tolist()
team_repo_monthly_colors = [
    team_repo_color_map.get(repo, "#b0b0b0") for repo in team_repo_monthly_order
]
team_repo_monthly["repo_rank"] = team_repo_monthly["repo_full_name"].map(
    {repo: rank for rank, repo in enumerate(team_repo_monthly_order, start=1)}
)

alt.Chart(team_repo_monthly, height=300).mark_bar(
    size=14, stroke="white", strokeWidth=0.6
).encode(
    x=alt.X("month:T", title="Month"),
    y=alt.Y("share:Q", title="Share of team activity", axis=alt.Axis(format="%")),
    color=alt.Color(
        "repo_full_name:N",
        title="Repository",
        scale=alt.Scale(domain=team_repo_monthly_order, range=team_repo_monthly_colors),
    ),
    order=alt.Order("repo_rank:Q"),
    tooltip=[
        "month:T",
        "repo_full_name:N",
        "total_activity:Q",
        alt.Tooltip("share:Q", format=".1%"),
    ],
    href="repo_url:N",
).properties(width="container").interactive()
```
