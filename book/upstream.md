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

# Upstream activity

This page summarizes where 2i2c spends its time in the Jupyter ecosystem and in our own technical repositories.
It's goal is to give us an idea for where we're shouldering maintenance and development burden and having impact.

Last updated: **{sub-ref}`today`**

:::{dropdown} Data sources
These plots use SQLite releases from
[`jupyter/github-data`](https://github.com/jupyter/github-data) and
[`2i2c-org/github-data`](https://github.com/2i2c-org/github-data).

TODO: This needs another few QA passes, but it's useful-enough that we are posting it as-is. See this issue to track QA checks we should implement: https://github.com/2i2c-org/kpis/issues/81
:::

```{code-cell} ipython3
---
tags: [remove-cell]
---
from pathlib import Path
import sqlite3
from subprocess import run

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from IPython.display import Markdown, display
import twoc
from twoc import colors as twoc_colors
from yaml import safe_load

twoc.set_plotly_defaults()

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
            title,
            state
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
            i.repo as repo_id,
            i.number as item_number,
            i.title as item_title,
            i.state as item_state,
            i.pull_request as is_pull_request
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


```{code-cell} ipython3
---
tags: [remove-cell]
---
# Filter for team activity
prs_upstream_team = prs_jupyter[prs_jupyter["is_team"]]
issues_upstream_team = issues_jupyter[issues_jupyter["is_team_issue_author"]]
comments_upstream_team = comments_jupyter[comments_jupyter["is_team_comment"]]


def build_repo_color_map(activity_df):
    """Build a color map for repos, colored by org."""
    if activity_df.empty:
        return {}
    orgs = sorted(activity_df["org"].dropna().unique())
    repo_color_map = {}
    for idx, org in enumerate(orgs):
        color = TWOC_PALETTE[idx % len(TWOC_PALETTE)]
        repos = activity_df.loc[activity_df["org"] == org, "repo_full_name"].dropna().unique()
        for repo in repos:
            repo_color_map[repo] = color
    return repo_color_map


def category_color_map(categories, palette):
    unique = list(dict.fromkeys(categories))
    return {name: palette[idx % len(palette)] for idx, name in enumerate(unique)}


upstream_activity_events = pd.concat(
    [
        prs_upstream_team[["org", "repo_full_name"]],
        issues_upstream_team[["org", "repo_full_name"]],
        comments_upstream_team[["org", "repo_full_name"]],
    ],
    ignore_index=True,
).dropna()
upstream_repo_color_map = build_repo_color_map(upstream_activity_events)


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
    # Calculate mean count per repo for ordering within orgs
    repo_means = counts.groupby("repo_full_name")["count"].mean().reset_index()
    repo_means["org"] = repo_means["repo_full_name"].str.split("/").str[0]
    # Sort by org, then by count (descending) within org
    repo_means = repo_means.sort_values(["org", "count"], ascending=[True, False])
    repo_order = repo_means["repo_full_name"].tolist()
    counts["repo_rank"] = counts["repo_full_name"].map(
        {repo: rank for rank, repo in enumerate(repo_order, start=1)}
    )
    return counts, repo_order


def stacked_repo_chart(df, repo_order, repo_color_map, title):
    color_map = {repo: repo_color_map.get(repo, "#b0b0b0") for repo in repo_order}
    fig = px.bar(
        df.sort_values("repo_rank"),
        x="month",
        y="count",
        color="repo_full_name",
        title=title,
        height=650,
        color_discrete_map=color_map,
        category_orders={"repo_full_name": repo_order},
        hover_data={"month": True, "repo_full_name": True, "count": True, "repo_url": True, "repo_rank": False},
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Count",
        legend_title="Repository",
        barmode="stack",
        legend=dict(font=dict(size=10)),
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.6)
    fig.show()


upstream_prs_authored_stack, upstream_prs_authored_order = prepare_repo_stack(
    prs_upstream_team, "merged_at", top_n=12
)
upstream_issues_opened_stack, upstream_issues_opened_order = prepare_repo_stack(
    issues_upstream_team, "created_at", top_n=12
)
# Comments on non-team PRs (support to community)
upstream_nonteam_pr_comments = comments_upstream_team[
    (~comments_upstream_team["is_team_issue_author"])
    & (comments_upstream_team["is_pull_request"].notna())
].copy()
upstream_nonteam_pr_comments_stack, upstream_nonteam_pr_comments_order = prepare_repo_stack(
    upstream_nonteam_pr_comments, "comment_created_at", top_n=12
)

# Comments on non-team issues (support to community)
upstream_nonteam_issue_comments = comments_upstream_team[
    (~comments_upstream_team["is_team_issue_author"])
    & (comments_upstream_team["is_pull_request"].isna())
].copy()
upstream_nonteam_issue_comments_stack, upstream_nonteam_issue_comments_order = prepare_repo_stack(
    upstream_nonteam_issue_comments, "comment_created_at", top_n=12
)


def make_pr_table(df, date_col="merged_at"):
    """Create a styled table of PRs for display."""
    recent = df[df[date_col] >= start_recent].copy()
    if recent.empty:
        return pd.DataFrame(columns=["Item", "Title", "Author", "Last Updated", "Status"]).style.hide(axis="index")
    recent = recent.sort_values(date_col, ascending=False)
    recent["Item"] = recent.apply(
        lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/pull/{r["number"]}" target="_blank">{r["repo_full_name"]}#{r["number"]}</a>',
        axis=1,
    )
    recent["Last Updated"] = recent[date_col].dt.strftime("%Y-%m-%d")
    recent["Status"] = "merged"
    return recent[["Item", "title", "author_login", "Last Updated", "Status"]].rename(
        columns={"title": "Title", "author_login": "Author"}
    ).style.hide(axis="index")


def make_issue_table(df, date_col="created_at"):
    """Create a styled table of issues for display."""
    recent = df[df[date_col] >= start_recent].copy()
    if recent.empty:
        return pd.DataFrame(columns=["Item", "Title", "Author", "Last Updated", "Status"]).style.hide(axis="index")
    recent = recent.sort_values(date_col, ascending=False)
    recent["Item"] = recent.apply(
        lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/issues/{r["number"]}" target="_blank">{r["repo_full_name"]}#{r["number"]}</a>',
        axis=1,
    )
    recent["Last Updated"] = recent[date_col].dt.strftime("%Y-%m-%d")
    recent["Status"] = recent["state"].fillna("unknown")
    return recent[["Item", "title", "issue_author", "Last Updated", "Status"]].rename(
        columns={"title": "Title", "issue_author": "Author"}
    ).style.hide(axis="index")


def make_comment_table(df, date_col="comment_created_at"):
    """Create a styled table of commented items for display."""
    recent = df[df[date_col] >= start_recent].copy()
    if recent.empty:
        return pd.DataFrame(columns=["Item", "Title", "Author", "Last Updated", "Status"]).style.hide(axis="index")
    recent = recent.sort_values(date_col, ascending=False)
    recent = recent.drop_duplicates(subset=["repo_full_name", "item_number", "comment_author"])
    recent["item_type"] = recent["is_pull_request"].apply(lambda x: "pull" if pd.notna(x) else "issues")
    recent["Item"] = recent.apply(
        lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/{r["item_type"]}/{int(r["item_number"])}" target="_blank">{r["repo_full_name"]}#{int(r["item_number"])}</a>',
        axis=1,
    )
    recent["Last Updated"] = recent[date_col].dt.strftime("%Y-%m-%d")
    recent["Status"] = recent["item_state"].fillna("unknown")
    return recent[["Item", "item_title", "comment_author", "Last Updated", "Status"]].rename(
        columns={"item_title": "Title", "comment_author": "Author"}
    ).style.hide(axis="index")
```

## Merged PRs authored by a team member

Reflects where we are making technical and community contributions.

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

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_pr_table(prs_upstream_team)
```

## Issues opened by a team member

Reflects where we are opening suggestions and design proposals for improvements or bugs.

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

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_issue_table(issues_upstream_team)
```

## Comments on PRs by non-team authors

Reflects where we are spending time reviewing and giving feedback for other contributors.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_repo_chart(
    upstream_nonteam_pr_comments_stack,
    upstream_nonteam_pr_comments_order,
    upstream_repo_color_map,
    "Comments on PRs by non-team authors, by repo",
)
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_comment_table(upstream_nonteam_pr_comments)
```

## Comments on issues by non-team authors

Reflects where we are providing support and discussion for users and other contributors.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_repo_chart(
    upstream_nonteam_issue_comments_stack,
    upstream_nonteam_issue_comments_order,
    upstream_repo_color_map,
    "Comments on issues by non-team authors, by repo",
)
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_comment_table(upstream_nonteam_issue_comments)
```


## Upstream leaderboards

[LFX Insights](https://insights.linuxfoundation.org/) is a service from the Linux Foundation to track community health and contributions.
We keep an eye on the contribution leaderboards to see where we, and the collaborators we work with, stand in relation to others.

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
```

## Activity in 2i2c repositories

Reflects where we're spending our time in 2i2c infrastructure repositories (these are all open source, but currently controlled by 2i2c).
```{code-cell} ipython3
---
tags: [remove-input]
---
team_repo_order = team_total_prs["repo_full_name"].tolist()
team_repo_color_map = category_color_map(team_repo_order, TWOC_PALETTE)

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

team_color_map = {repo: color for repo, color in zip(team_repo_monthly_order, team_repo_monthly_colors)}
fig = px.bar(
    team_repo_monthly.sort_values("repo_rank"),
    x="month",
    y="total_activity",
    color="repo_full_name",
    height=650,
    color_discrete_map=team_color_map,
    category_orders={"repo_full_name": team_repo_monthly_order},
    hover_data={"month": True, "repo_full_name": True, "total_activity": True, "repo_url": True, "repo_rank": False},
)
fig.update_layout(
    xaxis_title="Month",
    yaxis_title="PRs merged & Comments",
    legend_title="Repository",
    barmode="stack",
    legend=dict(font=dict(size=10)),
)
fig.update_traces(marker_line_color="white", marker_line_width=0.6)
fig.show()
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
# Show recent activity (PRs merged + comments) in 2i2c repos
# Combine PRs and comments into a unified table
prs_for_table = team_org_prs[team_org_prs["merged_at"] >= start_recent].copy()
prs_for_table["Item"] = prs_for_table.apply(
    lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/pull/{r["number"]}" target="_blank">{r["repo_full_name"]}#{r["number"]}</a>',
    axis=1,
)
prs_for_table["Title"] = prs_for_table["title"]
prs_for_table["Author"] = prs_for_table["author_login"]
prs_for_table["Last Updated"] = prs_for_table["merged_at"].dt.strftime("%Y-%m-%d")
prs_for_table["Type"] = "PR merged"
prs_for_table = prs_for_table[["Item", "Title", "Author", "Last Updated", "Type"]]

comments_for_table = team_org_comments[team_org_comments["comment_created_at"] >= start_recent].copy()
comments_for_table = comments_for_table.drop_duplicates(subset=["repo_full_name", "item_number", "comment_author"])
comments_for_table["item_type"] = comments_for_table["is_pull_request"].apply(lambda x: "pull" if pd.notna(x) else "issues")
comments_for_table["Item"] = comments_for_table.apply(
    lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/{r["item_type"]}/{int(r["item_number"])}" target="_blank">{r["repo_full_name"]}#{int(r["item_number"])}</a>',
    axis=1,
)
comments_for_table["Title"] = comments_for_table["item_title"]
comments_for_table["Author"] = comments_for_table["comment_author"]
comments_for_table["Last Updated"] = comments_for_table["comment_created_at"].dt.strftime("%Y-%m-%d")
comments_for_table["Type"] = "Comment"
comments_for_table = comments_for_table[["Item", "Title", "Author", "Last Updated", "Type"]]

combined_table = pd.concat([prs_for_table, comments_for_table], ignore_index=True)
combined_table = combined_table.sort_values("Last Updated", ascending=False)
combined_table.style.hide(axis="index")
```
