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
# =============================================================================
# IMPORTS AND SETUP
# =============================================================================
from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
from IPython.display import Markdown, display
import twoc
from twoc import colors as twoc_colors
from yaml import safe_load

twoc.set_plotly_defaults()

# 2i2c brand colors for consistent styling across charts
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
# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================
# These functions load GitHub activity data from SQLite databases.
# The databases are downloaded by: python book/scripts/download_upstream_data.py
# (or via `nox -s data`)
#
# Data sources:
# - jupyter/github-data: Activity in Jupyter ecosystem repos
# - 2i2c-org/github-data: Activity in 2i2c's own repos
#
# Database tables: users, repos, pull_requests, issues, issue_comments

DATA_ROOT = Path("_build/upstream-data")


def load_activity_from_db(db_path, start_date_str, team_logins):
    """
    Load PRs, issues, and comments from a single SQLite database.

    Returns three DataFrames (prs, comments, issues) with:
    - User logins and repo names joined in
    - org and repo_url columns derived from repo_full_name
    - is_team flags indicating whether authors are 2i2c team members
    """
    conn = sqlite3.connect(db_path)

    # Load lookup tables
    users = pd.read_sql("SELECT id as user_id, login FROM users", conn)
    repos = pd.read_sql("SELECT id as repo_id, full_name FROM repos", conn)
    users["user_id"] = users["user_id"].astype("Int64")

    # Load merged PRs since start date
    prs = pd.read_sql(
        """
        SELECT id as pr_id, user as user_id, merged_at, repo as repo_id, number, title
        FROM pull_requests
        WHERE merged_at >= ?
        """,
        conn,
        params=[start_date_str],
    )

    # Load issues since start date (includes PRs, filtered later)
    issues = pd.read_sql(
        """
        SELECT id as issue_id, user as issue_user_id, created_at, repo as repo_id,
               pull_request, number, title, state
        FROM issues
        WHERE created_at >= ?
        """,
        conn,
        params=[start_date_str],
    )

    # Load comments with their parent issue info
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

    # --- Join user and repo info into each DataFrame ---

    # PRs: add author login and repo name
    prs = prs.merge(users, on="user_id", how="left")
    prs = prs.merge(repos, on="repo_id", how="left")
    prs = prs.rename(columns={"login": "author_login", "full_name": "repo_full_name"})

    # Comments: add commenter login, issue author login, and repo name
    comments = comments.merge(
        users.rename(columns={"user_id": "comment_user_id", "login": "comment_author"}),
        on="comment_user_id", how="left"
    )
    comments = comments.merge(
        users.rename(columns={"user_id": "issue_user_id", "login": "issue_author"}),
        on="issue_user_id", how="left"
    )
    comments = comments.merge(repos, on="repo_id", how="left")
    comments = comments.rename(columns={"full_name": "repo_full_name"})

    # Issues: add author login and repo name, then filter out PRs
    issues = issues.merge(
        users.rename(columns={"user_id": "issue_user_id", "login": "issue_author"}),
        on="issue_user_id", how="left"
    )
    issues = issues.merge(repos, on="repo_id", how="left")
    issues = issues.rename(columns={"full_name": "repo_full_name"})
    issues = issues[issues["pull_request"].isna()]  # Keep only true issues

    # --- Add derived columns ---

    # Extract org name and build repo URL from repo_full_name (e.g., "jupyterhub/jupyterhub")
    for df in (prs, comments, issues):
        if not df.empty and df["repo_full_name"].notna().any():
            df["org"] = df["repo_full_name"].str.split("/").str[0]
            df["repo_url"] = "https://github.com/" + df["repo_full_name"].astype(str)
        else:
            df["org"] = None
            df["repo_url"] = None

    # Parse date columns
    prs["merged_at"] = pd.to_datetime(prs["merged_at"], utc=True, errors="coerce")
    comments["comment_created_at"] = pd.to_datetime(comments["comment_created_at"], utc=True, errors="coerce")
    issues["created_at"] = pd.to_datetime(issues["created_at"], utc=True, errors="coerce")

    # Flag activity by team members
    prs["is_team"] = prs["author_login"].isin(team_logins)
    comments["is_team_comment"] = comments["comment_author"].isin(team_logins)
    comments["is_team_issue_author"] = comments["issue_author"].isin(team_logins)
    issues["is_team_issue_author"] = issues["issue_author"].isin(team_logins)

    return prs, comments, issues


def load_activity(db_paths, start_date_str, team_logins):
    """Load and concatenate activity from multiple database files."""
    all_prs, all_comments, all_issues = [], [], []

    for db_path in db_paths:
        prs, comments, issues = load_activity_from_db(db_path, start_date_str, team_logins)
        all_prs.append(prs)
        all_comments.append(comments)
        all_issues.append(issues)

    return (
        pd.concat(all_prs, ignore_index=True) if all_prs else pd.DataFrame(),
        pd.concat(all_comments, ignore_index=True) if all_comments else pd.DataFrame(),
        pd.concat(all_issues, ignore_index=True) if all_issues else pd.DataFrame(),
    )
```

```{code-cell} ipython3
---
tags: [remove-cell]
---
# =============================================================================
# LOAD DATA
# =============================================================================
# Load team member GitHub logins from config file
team_logins = safe_load(Path("data/team.yml").read_text())

# Define date ranges: full year for charts, recent 2 months for tables
today = pd.Timestamp.utcnow().normalize()
start_year = today - pd.DateOffset(years=1)
start_recent = today - pd.DateOffset(months=2)
start_year_str = start_year.strftime("%Y-%m-%dT%H:%M:%SZ")

# Load upstream data (downloaded by: nox -s data, or scripts/download_upstream_data.py)
jupyter_db_paths = sorted((DATA_ROOT / "jupyter").glob("*.db"))
team_db_paths = sorted((DATA_ROOT / "2i2c").glob("*.db"))

if not jupyter_db_paths:
    raise FileNotFoundError(
        f"No database files found in {DATA_ROOT / 'jupyter'}. "
        "Run `nox -s data` or `python book/scripts/download_upstream_data.py` first."
    )

prs_jupyter, comments_jupyter, issues_jupyter = load_activity(
    jupyter_db_paths, start_year_str, team_logins
)

# Load 2i2c org data (our own repos)
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
# =============================================================================
# VISUALIZATION HELPERS
# =============================================================================

def build_color_map(repos, palette=TWOC_PALETTE):
    """
    Assign colors to repositories, grouping by org.
    All repos in the same org get the same color.
    """
    if not repos:
        return {}

    # Get unique orgs
    orgs = sorted(set(r.split("/")[0] for r in repos if "/" in r))
    org_colors = {org: palette[i % len(palette)] for i, org in enumerate(orgs)}

    return {repo: org_colors.get(repo.split("/")[0], "#b0b0b0") for repo in repos}


def prepare_monthly_counts(df, date_col, top_n=12):
    """
    Prepare data for a stacked bar chart showing monthly activity by repo.

    Returns:
        counts: DataFrame with columns [month, repo_full_name, repo_url, count]
        repo_order: List of repo names ordered by total activity (descending)
    """
    df = df.dropna(subset=[date_col, "repo_full_name"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["month", "repo_full_name", "repo_url", "count"]), []

    # Convert dates to month periods
    df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()

    # Keep only top N repos by total activity
    totals = df.groupby("repo_full_name").size().sort_values(ascending=False)
    top_repos = totals.head(top_n).index
    df = df[df["repo_full_name"].isin(top_repos)]

    # Count activity per month per repo
    counts = df.groupby(["month", "repo_full_name", "repo_url"]).size().reset_index(name="count")

    # Order repos: by org name, then by count within org
    repo_order = totals.head(top_n).index.tolist()

    return counts, repo_order


def stacked_bar_chart(df, repo_order, title):
    """Create a stacked bar chart of monthly activity by repository."""
    if df.empty:
        display(Markdown(f"*No data available for: {title}*"))
        return

    color_map = build_color_map(repo_order)

    fig = px.bar(
        df,
        x="month",
        y="count",
        color="repo_full_name",
        title=title,
        height=650,
        color_discrete_map=color_map,
        category_orders={"repo_full_name": repo_order},
        hover_data={"month": True, "repo_full_name": True, "count": True, "repo_url": True},
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


def make_activity_table(df, date_col, item_type="pr", author_col="author_login"):
    """
    Create a styled HTML table of recent activity.

    Args:
        df: DataFrame with activity data
        date_col: Column name containing the date
        item_type: "pr", "issue", or "comment" - determines URL path
        author_col: Column name containing the author
    """
    recent = df[df[date_col] >= start_recent].copy()
    if recent.empty:
        return pd.DataFrame(columns=["Item", "Title", "Author", "Date"]).style.hide(axis="index")

    recent = recent.sort_values(date_col, ascending=False)

    # For comments, dedupe by item (one row per item per author)
    if item_type == "comment":
        recent = recent.drop_duplicates(subset=["repo_full_name", "item_number", author_col])

    # Build GitHub URL based on item type
    if item_type == "comment":
        # Comments link to either PR or issue based on is_pull_request field
        recent["url_type"] = recent["is_pull_request"].apply(lambda x: "pull" if pd.notna(x) else "issues")
        recent["Item"] = recent.apply(
            lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/{r["url_type"]}/{int(r["item_number"])}">{r["repo_full_name"]}#{int(r["item_number"])}</a>',
            axis=1,
        )
        title_col = "item_title"
    else:
        url_path = "pull" if item_type == "pr" else "issues"
        recent["Item"] = recent.apply(
            lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/{url_path}/{r["number"]}">{r["repo_full_name"]}#{r["number"]}</a>',
            axis=1,
        )
        title_col = "title"

    recent["Date"] = recent[date_col].dt.strftime("%Y-%m-%d")

    return recent[["Item", title_col, author_col, "Date"]].rename(
        columns={title_col: "Title", author_col: "Author"}
    ).style.hide(axis="index")
```

```{code-cell} ipython3
---
tags: [remove-cell]
---
# =============================================================================
# PREPARE UPSTREAM (JUPYTER ECOSYSTEM) DATA
# =============================================================================
# Filter to only team member activity in Jupyter ecosystem repos

prs_upstream_team = prs_jupyter[prs_jupyter["is_team"]]
issues_upstream_team = issues_jupyter[issues_jupyter["is_team_issue_author"]]
comments_upstream_team = comments_jupyter[comments_jupyter["is_team_comment"]]

# Prepare chart data for each category
upstream_prs_data, upstream_prs_order = prepare_monthly_counts(prs_upstream_team, "merged_at")
upstream_issues_data, upstream_issues_order = prepare_monthly_counts(issues_upstream_team, "created_at")

# Comments on non-team PRs = reviewing community contributions
upstream_pr_reviews = comments_upstream_team[
    (~comments_upstream_team["is_team_issue_author"]) &
    (comments_upstream_team["is_pull_request"].notna())
]
upstream_pr_reviews_data, upstream_pr_reviews_order = prepare_monthly_counts(upstream_pr_reviews, "comment_created_at")

# Comments on non-team issues = supporting community
upstream_issue_support = comments_upstream_team[
    (~comments_upstream_team["is_team_issue_author"]) &
    (comments_upstream_team["is_pull_request"].isna())
]
upstream_issue_support_data, upstream_issue_support_order = prepare_monthly_counts(upstream_issue_support, "comment_created_at")
```

## Merged PRs authored by a team member

Reflects where we are making technical and community contributions.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_bar_chart(upstream_prs_data, upstream_prs_order, "Merged PRs authored by a team member, by repo")
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_activity_table(prs_upstream_team, "merged_at", item_type="pr", author_col="author_login")
```

## Issues opened by a team member

Reflects where we are opening suggestions and design proposals for improvements or bugs.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_bar_chart(upstream_issues_data, upstream_issues_order, "Issues opened by a team member, by repo")
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_activity_table(issues_upstream_team, "created_at", item_type="issue", author_col="issue_author")
```

## Comments on PRs by non-team authors

Reflects where we are spending time reviewing and giving feedback for other contributors.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_bar_chart(upstream_pr_reviews_data, upstream_pr_reviews_order, "Comments on PRs by non-team authors, by repo")
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_activity_table(upstream_pr_reviews, "comment_created_at", item_type="comment", author_col="comment_author")
```

## Comments on issues by non-team authors

Reflects where we are providing support and discussion for users and other contributors.

```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_bar_chart(upstream_issue_support_data, upstream_issue_support_order, "Comments on issues by non-team authors, by repo")
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
make_activity_table(upstream_issue_support, "comment_created_at", item_type="comment", author_col="comment_author")
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
# =============================================================================
# PREPARE 2I2C ORG DATA
# =============================================================================
# Activity in 2i2c's own repositories (infrastructure, docs, etc.)

# Filter to team activity, excluding non-technical repos
team_org_prs = team_prs[team_prs["is_team"]]
team_org_comments = team_comments[team_comments["is_team_comment"]]

EXCLUDED_REPOS = {"2i2c-org/2i2c-org.github.io", "2i2c-org/team-compass"}
team_org_prs = team_org_prs[~team_org_prs["repo_full_name"].isin(EXCLUDED_REPOS)]
team_org_comments = team_org_comments[~team_org_comments["repo_full_name"].isin(EXCLUDED_REPOS)]

# Combine PRs and comments for total activity chart
team_activity = pd.concat([
    team_org_prs[["repo_full_name", "repo_url", "merged_at"]].rename(columns={"merged_at": "date"}),
    team_org_comments[["repo_full_name", "repo_url", "comment_created_at"]].rename(columns={"comment_created_at": "date"}),
], ignore_index=True)

team_activity_data, team_activity_order = prepare_monthly_counts(team_activity, "date", top_n=8)
```

## Activity in 2i2c repositories

Reflects where we're spending our time in 2i2c infrastructure repositories (these are all open source, but currently controlled by 2i2c).
```{code-cell} ipython3
---
tags: [remove-input]
---
stacked_bar_chart(team_activity_data, team_activity_order, "Activity in 2i2c repositories (PRs merged + comments)")
```

**Table of issues and PRs that match the plot above**:

```{code-cell} ipython3
---
tags: [remove-input, hide-output]
---
# Combine recent PRs and comments into one table
prs_table = team_org_prs[team_org_prs["merged_at"] >= start_recent].copy()
prs_table["Item"] = prs_table.apply(
    lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/pull/{r["number"]}">{r["repo_full_name"]}#{r["number"]}</a>',
    axis=1,
)
prs_table["Date"] = prs_table["merged_at"].dt.strftime("%Y-%m-%d")
prs_table["Type"] = "PR merged"
prs_table = prs_table[["Item", "title", "author_login", "Date", "Type"]].rename(
    columns={"title": "Title", "author_login": "Author"}
)

comments_table = team_org_comments[team_org_comments["comment_created_at"] >= start_recent].copy()
comments_table = comments_table.drop_duplicates(subset=["repo_full_name", "item_number", "comment_author"])
comments_table["url_type"] = comments_table["is_pull_request"].apply(lambda x: "pull" if pd.notna(x) else "issues")
comments_table["Item"] = comments_table.apply(
    lambda r: f'<a href="https://github.com/{r["repo_full_name"]}/{r["url_type"]}/{int(r["item_number"])}">{r["repo_full_name"]}#{int(r["item_number"])}</a>',
    axis=1,
)
comments_table["Date"] = comments_table["comment_created_at"].dt.strftime("%Y-%m-%d")
comments_table["Type"] = "Comment"
comments_table = comments_table[["Item", "item_title", "comment_author", "Date", "Type"]].rename(
    columns={"item_title": "Title", "comment_author": "Author"}
)

combined = pd.concat([prs_table, comments_table], ignore_index=True).sort_values("Date", ascending=False)
combined.style.hide(axis="index")
```
