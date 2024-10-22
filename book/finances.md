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

# Revenue projections

This document shows 2i2c's revenue projections by contract, and predicts 2i2c's monthly income along with its costs using data from our [Opportunities AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblBTPDI1nKoq8wOL/viwuJxmlTnW1VZxIm?blocks=hide).

When built via Jupyter Book, all opportunities are anonymized.
If you want de-anonymized opportunities, run the notebook locally.

:::{admonition} To run this notebook locally
:class: dropdown
To see the visualizations locally, follow these steps:

1. Get an API key for AirTable (see [our team compass docs on AirTable](https://compass.2i2c.org/administration/airtable/)) and store it in an environment variable called `AIRTABLE_AP_KEY`.
2. Download the latest data:

   ```bash
   python book/scripts/download_airtable_data.py
   ```
3. Run this notebook from top to bottom.

There are several important fields in both {kbd}`opportunities` and {kbd}`Contracts`, they're described below:

- {kbd}`Start Date` / {kbd}`End Date`: The starting and ending date of a contract.
- {kbd}`Amount`: The total budget amount in the grant.
- {kbd}`Amount for 2i2c`: The budget that is available to 2i2c (if <100% of the amount total)
- {kbd}`CSS %`: The % that CS&S will take for their indirect costs.
:::

:::{admonition} How numbers are prioritized
:class: dropdown
This notebook tries to use the _most accurate data that we've got_.
For example, contracts are usually more accurate than opportunities.
For data about dates and $$ amounts, here's the logic we follow:

1. {kbd}`Amount (from Contract)`. If we have a contract with CS&S for this Lead, use this.
2. {kbd}`Amount (from Opportunities)`. If we have no contract, use our opportunities airtable for a best estimate.
:::

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import datetime
import os
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly_express as px

# Apply 2i2c default styles
import twoc
from twoc.dates import round_to_nearest_month
from IPython.display import Markdown
from itables import show as ishow
from plotly.graph_objects import Figure
from plotly.subplots import make_subplots
import ipywidgets as widgets
from IPython.display import display


twoc.set_plotly_defaults()

# This just suppresses a warning
pd.set_option("future.no_silent_downcasting", True)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
def convert_column_string_to_object(string):
    """Convert an airtable column string to a Python object.

    Linked records / rollups will have string representations of their value
    so this converts it to a python object we can manipulate.
    """
    if not isinstance(string, str):
        return string
    obj = eval(string)
    if isinstance(obj, list) and (len(obj) == 1):
        obj = obj[0]
    return obj
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Costs

Costs are manually calculated for now from [this Google Sheet](https://docs.google.com/spreadsheets/d/1OpKfPSIiFTY28OkV6--MhZygvdLVSdmpagjlnge2ELc/edit?usp=sharing). These **exclude our Fiscal Sponsor Fee** (because this fee is already subtracted from revenue projections below).

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stdout, remove-stderr]
---
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRUl-GB46-plmuYxaZSK_IQxgzYI_MBGN8YffTdYS_267YqPrXvROgIQGT-Xspeug__Ut6nRPRDHGZ5/pub?gid=1482549235&single=true&output=csv"
costs = pd.read_csv(url, header=2).dropna()
costs = costs.rename(columns={"Summary": "Date"})
costs["Date"] = pd.to_datetime(costs["Date"])
                     
# These costs *exclude* our fiscal sponsor fee.
# This is because all of the `opportunities` data subtracts the FSP fee in its amount
MONTHLY_COSTS = costs["Expenses"].head(5).mean()
ANNUAL_COSTS = MONTHLY_COSTS * 12

md = f"""
- **Assumed annual costs (no FSP)**: ${ANNUAL_COSTS:,.0f}
- **Assumed monthly costs (no FSP)**: ${MONTHLY_COSTS:,.0f}
"""
Markdown(md)
# costs.tail()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Revenue

[Our Opportunities AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblBTPDI1nKoq8wOL/viwuJxmlTnW1VZxIm?blocks=hide) has all of our potential sources of revenue, as well as links to any contracts for opportunities we have won. The view linked above is the source of data for this page.

Opportunities are broken into two stages:

```{list-table}
- * **Opportunities**
  * [link to AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblBTPDI1nKoq8wOL/viwcsrE83taP6GhSl?blocks=hide)
  * Potential sources of revenue. Each has a % probability of success. When an opportunity is "won", it gets a contract and we stop treating it as an opportunity.
- * **Contracts**
  * [link to AirTable](https://airtable.com/appbjBTRIbgRiElkr/tbliwB70vYg3hlkb1/viwGdDgmTcxfnsRDC?blocks=hide)
  * Legal agreements with a total value, start, and stop date. Revenue is treated as 100% reliable.
```

Opportunities are broken into two categories.

```{list-table}
- * **Giving**
  * Financial contributions given to support our mission without expectation of direct material benefit to the donor.
- * **Services**
  * Income generated through services we provide in exchange for payment.
```

````{admonition} Expected total amounts
:class: dropdown

We add a column for the *weighted* total amount to account for the fact that the opportunity may not come through.
This helps us calculate the _total expected amount of revenue_:

`total expected amount` = `opportunity total amounts` * `probability of each opportunity being won`

or if you're a mathy person:

```{math}

E \left[ \sum(opportunities) \right] = \sum_{1}^{n\_opportunities} opportunity\_total * opportunity\_probability = \sum \left( E[opportunities] \right)

```
````


````{admonition} We amortize total amounts over months
:class: dropdown

We spread the total revenue for an opportunity/contract into equal monthly amounts over the total lifetime of the contract.
````

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Read in the latest data from AirTable.
# To update the data, run scripts/download_airtable_data.py
opportunities = pd.read_csv("./data/airtable-opportunities.csv")

# Remove all lost and abandoned opportunities
opportunities = opportunities.replace("Closed—won", "Committed")
opportunities = opportunities.loc[~opportunities["Stage"].str.contains("Closed")]

# Drop opportunities without a value/start/end
opportunities = opportunities.dropna(subset=["Opportunity Value", "Target Start Date", "Target End Date", "Probability Success"])

# Rename to standardized column mapping
rename = {
    "Start Date (for projections)": "Start Date",
    "End Date (for projections)": "End Date",
    "Opportunity Name": "Name",
}
opportunities = opportunities.rename(columns=rename)

# Convert probability to a %
opportunities["Probability Success"] = opportunities["Probability Success"] / 5
PROBABILITY_CUTOFF = .4
opportunities = opportunities.query("`Probability Success` >= @PROBABILITY_CUTOFF")

# Choose categories based on stage and category
for ix, irow in opportunities.iterrows():
    if (irow["Stage"] == "Committed") or (irow["Stage"] == "Contract Admin"):
        opportunities.loc[ix, "Category"] = f"{irow['Category']}-Committed"

        # For committed opportunities, set the expected value to 100% 
        opportunities.loc[ix, "Weighted Value for 2i2c"] = irow["Value for 2i2c"]
    else:
        opportunities.loc[ix, "Category"] = f"{irow['Category']}-Prospective"

# Ensure numeric values
numeric_cols = ["Weighted Value for 2i2c", "Value for 2i2c"]
for col in numeric_cols:
    opportunities.loc[:, col] = opportunities.loc[:, col].astype(float)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
Markdown(f"Note: All projections **exclude opportunities with < %{PROBABILITY_CUTOFF*100:.0f} probability**.")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# If we want to look at the opportunities that were dropped
# ishow(opportunities, pageLength=50)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# TURNING THIS OFF because we'll password-protect this page for now.
# Anonymize opportunities if we are in a CI/CD environment because this will be public
# if "GITHUB_ACTION" in os.environ:
#     for ix, name in opportunities["Name"].items():
#         opportunities.loc[ix, "Name"] = f"Opportunity {ix}"
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Convert date columns to DateTime objects
date_cols = ["Start Date", "End Date"]
opportunities = opportunities.dropna(subset=date_cols)
for col in date_cols:
    opportunities.loc[:, col] = pd.to_datetime(opportunities[col])
    # Round any dates to the nearest month start.
    # This controls for the fact that some dates are the 1st, others the 31st.
    opportunities.loc[:, col] = opportunities[col].apply(lambda x: round_to_nearest_month(x))
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Generate a month entry for each lead with its amortized monthly amount
amortized_records = []

for ix, irow in opportunities.iterrows():
    # We *exclude* the month of the right-most date because we know it is always the 1st
    # This is because of the month rounding we did above
    dates = pd.date_range(
        irow["Start Date"], irow["End Date"], freq="MS", inclusive="left"
    )
    n_months = len(dates)
    for date in dates:
        amortized_records.append(
            {
                "Date": date,
                "Total amount": irow["Value for 2i2c"],
                "Monthly amount": irow["Value for 2i2c"] / n_months,
                "Monthly amount (expected)": irow["Weighted Value for 2i2c"] / n_months,
                "Category": irow["Category"],
                "Stage": irow["Stage"],
                "Name": irow["Name"],
                "Probability Success": irow["Probability Success"],
            }
        )
amortized_records = pd.DataFrame(amortized_records)

# Drop all records before January 2022 since data is unreliable before then
amortized_records = amortized_records.query("Date >= '2022-01-01'")
amortized_records = amortized_records.sort_values("Monthly amount", ascending=False)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Budget projections

The following plots show our revenue projections under different sets of assumptions. They go 12 months into the future.
There are three key figures, described below.

1. Our **weighted projected revenue** where opportunity totals are weighted by their expected probability.
2. Our **committed revenue** which only includes opportunities with an active contract or awaiting contracting.
3. Our **best-case scenario total revenue** which reflects revenue if every lead is successful.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Preparing figures for visualization
legend_orientation = dict(
    orientation="h",  # Horizontal orientation
    yanchor="bottom",
    y=1.02,
    xanchor="center",
    x=0.5,
)

def update_layout(fig):
    fig.update_layout(
        legend=legend_orientation,
        legend_title_text="",
        yaxis_title="",
        xaxis_title="",
    )


def write_image(fig, path, fig_height=350):
    """Write an image for a plotly figure to a path while applying common styling."""
    # Create a new figure object
    fig = Figure(fig)
    # Update font size for print
    fig.update_layout(
        height=fig_height,
        legend_font_size=10,
        title=dict(
            font=dict(
                size=12,
            )
        ),
    )
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(path, scale=4)

# Historical query for the last 2 months through the next 12 months
today = datetime.datetime.today()
date_past = round_to_nearest_month(today - datetime.timedelta(days=30 * 3))
date_future = round_to_nearest_month(today + datetime.timedelta(days=30 * 12))

# Query for date range
qu_date = f"Date >= '{date_past:%Y-%m-%d}' and Date < '{date_future:%Y-%m-%d}'"
qu_committed = f"`Stage` in ['Committed', 'Contract Admin']"

# Colors that help with plotting
colors = {
    "Services-Committed": twoc.colors["bigblue"],
    "Giving-Committed": twoc.colors["coral"],
    "Giving-Prospective": "lightcoral",
    "Services-Prospective": "lightblue", 
}

bar_kwargs = dict(
    color="Category",
    category_orders={"Category": colors.keys()},
    color_discrete_map=colors,
    hover_name = "Name",
    hover_data={
            "Monthly amount": ":$,.0f",
            "Monthly amount (expected)": ":$,.0f",
            "Total amount": ":$,.0f",
            "Probability Success": ":%.0f",
    },
)


figures = {}
labels = ["committed", "estimated", "full", "estimated by category"]
for label in labels:
    # Bar plot of revenue
    data_plot = amortized_records.query(qu_date)
    if label == "full":
        # If we are using total amount, only use records with >= 40% chance success
        iname = "Monthly amount"
        title = "Monthly Revenue (full contract revenue)"
    elif label == "estimated":
        iname = "Monthly amount (expected)"
        title = "Monthly Revenue (weighted by probability success)"
    elif "category" in label:
        data_plot = data_plot.groupby(["Date", "Category"]).sum("Monthly amount (expected)")
        data_plot = data_plot.reset_index()
        data_plot["Name"] = data_plot["Category"]
        iname = "Monthly amount (expected)"
        title = "Monthly Revenue (weighted by probability success)"
    else:
        iname = "Monthly amount"
        data_plot = data_plot.query(qu_committed)
        title = "Committed revenue"

    figservice = px.bar(
        data_plot,
        x="Date",
        y=iname,
        title=title,
        **bar_kwargs,
    )
    figservice.update_traces(marker_line_width=0.2)

    # Dotted line plot of costs
    figservice.add_scatter(
        x=costs.query(qu_date)["Date"],
        y=costs.query(qu_date)["Expenses"],
        mode="lines",
        line_shape="hv",
        line_dash="dash",
        line_width=4,
        line_color="black",
        name="Costs",
    )
    update_layout(figservice)
    figures[label] = figservice

# Create tab contents using Output widgets
tabs = []
for ilabel in labels:
    itab = widgets.Output()
    with itab:
        figures[ilabel].show()
    tabs.append(itab)

# Create the tab widget
tabs = widgets.Tab(tabs)
for ii, ilabel in enumerate(labels):
    tabs.set_title(ii, ilabel)

# Display the tab widget
display(tabs)
```
