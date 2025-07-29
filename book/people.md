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

# People KPIs

+++

This page describes KPIs related to our collective health as a team as well as individually.

+++

## Time off / vacation

+++ {"editable": true, "slideshow": {"slide_type": ""}}

This section uses the **GitHub CLI** to download time off data from the [`2i2c-org/meta` Time Off board](https://github.com/orgs/2i2c-org/projects/39), and uses Python to visualize how our team is doing.

2i2c staff are [expected to take at least 40 days off leave per year](https://team-compass.2i2c.org/people/time-off/). Using the data above, we can calculate how many total days of leave each person has taken this year so far.

:::{admonition} The goal is to make sure we are taking enough time off!
:class: warning
Time off is critical, and having a "no limit" time off policy often means people don't take enough time.
The main purpose of this notebook is to visualize our progress towards taking *enough time off each year*.
Ideally, we want each member of our team to hover around **40 days off a year**.

It is better to over-shoot 40 days rather than under-shoot it!
:::

:::{admonition} Instructions to run this notebook
:class: dropdown

1. [Install the GitHub CLI](https://cli.github.com/)
    - Once you install, ensure the GitHub CLI is authorized to connect with GitHub via your account:
      
      ```bash
      gh auth login
      ```
2. Install the requirements for this notebook:
   ```bash
   pip install -r requirements.txt
   ```
3. Run all the cells in this notebook and look at the visualizations at the bottom.
:::

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

### Download latest time off data from our GitHub Project

Use the `gh` cli to download data from the [2i2c Time Off board](https://github.com/orgs/2i2c-org/projects/39).

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import os
import re
from datetime import datetime, timedelta
from json import loads
from pathlib import Path
from subprocess import run

import numpy as np
import pandas as pd
from yaml import safe_load
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Use the GH CLI to print all of the records in our time off table
LIMIT_LENGTH = 1000
cmd = f"gh project item-list 39 --owner 2i2c-org -L {LIMIT_LENGTH} --format json"
out = run(cmd.split(), text=True, capture_output=True, check=True)

# Strip the output of all color codes and parse it as JSON, then a dataframe
def strip_ansi(text):
    """
    Remove ANSI escape codes from a string.

    Args:
    text (str): The input string containing ANSI escape codes.

    Returns:
    str: The input string with all ANSI escape codes removed.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


json = loads(strip_ansi(out.stdout))
team = safe_load(Path("data/team.yml").read_text())
team = [ii.lower() for ii in team]
```

```{code-cell} ipython3
if len(json["items"]) == LIMIT_LENGTH:
    raise ValueError(f"Downloaded our max possible items ({LIMIT_LENGTH}), delete some items or increase the LIMIT_LENGTH for days off searches")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

## Data prep and cleaning

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# This is the expected time off each year for each team member
ANNUAL_EXPECTED_DAYS_OFF = 40

# Dates to help with plotting
today = datetime.today()
# Use the start of the calendar year for tracking time off
start_cal = datetime(year=today.year, month=1, day=1)
end_cal = datetime(year=today.year, month=12, day=31)

# How many days we expect each person to accumulate by the end of our viz window
num_days_to_be_on_target = int(
    ((end_cal - start_cal).days / 365) * ANNUAL_EXPECTED_DAYS_OFF
)
days_expected_by_today = int(
    ((today - start_cal).days / 365) * ANNUAL_EXPECTED_DAYS_OFF
)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Turn into dataframe
df = pd.DataFrame(json["items"])

# Extract assignees as strings instead of lists
def extract_assignee(val):
    if isinstance(val, list):
        val = val[0]
    return val.lower()
df = df.dropna(subset=["assignees"])
df["assignees"] = df["assignees"].map(extract_assignee)

# Only keep time off for our window
# Limit last day to the last day of the year
date_cols = ["first day", "last day"]
for col in date_cols:
    df.loc[:, col] = pd.to_datetime(df[col])
df["last day"] = df["last day"].map(lambda a: np.min([a, end_cal]))

# Drop entries with missing dates
df = df.dropna(subset=["first day", "last day"])

# Only keep entries for our current team
df = df.query("assignees in @team")

# Replace missing types with vacation
df["type"] = df["type"].replace(pd.NA, "Vacation")
print(f"Found {len(df)} away entries (including half-days and conferences etc)...")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Requests for time off and reduced time

Below we show all requests for "reduced time".
This includes time off, as well as "reduced" days (e.g. half-days) and conference days.

:::{admonition} Half days and conferences are not time off
:class: warning
Time off should allow you to detach from work and focus on yourself.
We don't include time spent at conferences or partial days in time-off visualizations. If you spend part of the day working, or spend the time at a professional event, you don't really detach. So, while conferences and half days are still good, we we do not treat this as part of our time off target.
:::

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
import plotly.io as pio
import plotly.express as px
pio.renderers.default = "notebook"

df["last day plus one"] = df["last day"] + timedelta(days=1)

# Calculate number of days off by generating a range of *business days* and counting the list.
# This ensures we exclude weekends
df["days_off"] = df.apply(
    lambda a: len(pd.bdate_range(a["first day"], a["last day"])), axis=1
)

fig = px.timeline(
    df,
    x_start="first day",
    x_end="last day plus one",
    y="assignees",
    title="Days off over this calendar year",
    height=700,
    color="type",
    hover_data=["days_off"],
)
fig.update_xaxes(range=[start_cal, end_cal])
fig.add_vline(pd.Timestamp.today())
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Accumulated time off this year

Visualize the time off that people taken this calendar year.
Our target is 40 days per year, and it's better to over- than under-shoot.

:::{admonition} Double-click a name to see its line
You can double-click a name and it will only show the line for that line.
This way you can check yourself to make sure you're on track!
:::

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Apply consistent labeling to time off requests
skip_title_entries_with = ["reduce", "conference", "half", "afternoon", "morning"]
for ii in skip_title_entries_with:
    df = df.loc[~df["title"].str.lower().str.contains(ii).values]
print(f"Found {len(df)} time off entries...")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Accumulate days off over each entry per person
df_cumulative = df.query("(`first day` >= @start_cal)")
cumulative = []
for person, idata in df_cumulative.groupby("assignees"):
    # Add an entry for the first day of the period we visualize
    idata = idata.reset_index(drop=True)
    idata.loc[len(idata)] = {"days_off": 0, "assignees": person, "first day": start_cal}
    # Now sort so that it's linear in time
    idata = idata.sort_values("first day")
    idata["cumulative"] = idata["days_off"].cumsum()
    cumulative.append(
        idata[["assignees", "first day", "last day", "days_off", "cumulative"]]
    )
cumulative = pd.concat(cumulative)
cumulative = cumulative.rename(columns={"assignees": "person"})
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Calculate the "burn rate" of time off we'd expect if team members were hitting their 40 day target.
expected = pd.DataFrame(
    [
        {"day": start_cal, "amount": 0},
        {"day": end_cal, "amount": num_days_to_be_on_target},
    ],
)
expected["day"] = pd.to_datetime(expected["day"])
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Visualize over time
n_people = cumulative["person"].unique().shape[0]
colormap = px.colors.sample_colorscale("Portland", n_people)
fig = px.line(
    cumulative,
    x="first day",
    y="cumulative",
    color="person",
    line_shape="hv",
    height=700,
    hover_data=["last day", "days_off"],
    color_discrete_sequence=colormap,
    title="Accumulated time off over this calendar year",
)
fig.add_vline(pd.Timestamp.today(), line_dash="dash")
fig.add_trace(
    px.line(
        expected,
        x="day",
        y="amount",
        line_dash_sequence=["dot"],
        color_discrete_sequence=["black"],
    ).data[0]
)
fig.update_xaxes(range=[start_cal, end_cal])
fig.update_yaxes(range=[0, 50])
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Below is a table to describe how our team is doing at taking enough time off.
It uses a reference target of 40 days per year.

Remember it's **better to take off too many days off than too little**.
Those with a `difference` value above 0 should take more days off!

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
time_off_by_person = (
    cumulative.query("`first day` < @today")
    .groupby("person")
    .agg({"cumulative": "max"})
    .rename(columns={"cumulative": "taken"})
)
time_off_by_person["total"] = cumulative.groupby("person")[["cumulative"]].max()
time_off_by_person["planned"] = time_off_by_person["total"] - time_off_by_person["taken"]
time_off_by_person["difference planned vs annual target"] = (
    ANNUAL_EXPECTED_DAYS_OFF - (time_off_by_person["taken"] + time_off_by_person["planned"])
)
time_off_by_person["difference taken vs expected by today"] = (
    days_expected_by_today - time_off_by_person["taken"]
)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
sorted_names = time_off_by_person.sort_values("total").index.values
fig = px.bar(
    time_off_by_person.reset_index(),
    y="person",
    x=["taken", "planned"],
    hover_data=["difference planned vs annual target", "difference taken vs expected by today"],
    title="Planned time off (blue) compared with\nexpected time off by today (red) and annual target (black)",
    category_orders={"person": sorted_names},
)
fig.add_vline(days_expected_by_today, line_color="red", line_dash="dash")
fig.add_vline(ANNUAL_EXPECTED_DAYS_OFF, line_dash="dash")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Accumulated time off in the last six months

This shows time off accumulated over the last six months, rather than the last calendar year.
This gives us an idea for how we're accumulating time off more recently in general.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Three month window in the past/future
start_win = today - timedelta(30 * 6)
end_win = today + timedelta(30 * 1)

# 6 month window so expected days is 40 / 2
expected_n_days_in_win = 20
# Calculate the "burn rate" of time off we'd expect if team members were hitting their 40 day target.
expected = pd.DataFrame(
    [{"day": start_win, "amount": 0}, {"day": today, "amount": expected_n_days_in_win}],
)
expected["day"] = pd.to_datetime(expected["day"])
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Visualize over time
fig = px.line(
    cumulative.query("`first day` >= @start_win"),
    x="first day",
    y="cumulative",
    color="person",
    line_shape="hv",
    height=700,
    hover_data=["last day", "days_off"],
    color_discrete_sequence=colormap,
    title="Accumulated time off in a 6-month window",
)
fig.add_vline(pd.Timestamp.today(), line_dash="dash")
fig.add_trace(
    px.line(
        expected,
        x="day",
        y="amount",
        line_dash_sequence=["dot"],
        color_discrete_sequence=["black"],
    ).data[0]
)
fig.update_xaxes(range=[start_win, end_win])
fig.update_yaxes(range=[0, 35])
```
