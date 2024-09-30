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

:::{admonition} BROKEN DUE TO TABLE CHANGES
Our sales airtable has changed and we must update it to the new structure.
See https://github.com/2i2c-org/kpis/issues/51 for tracking issue.
:::

This document shows 2i2c's historical revenue data by contract, and predicts 2i2c's monthly income along with its costs using data from our [Leads AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblmRU6U53i8o7z2I/viw8xzzSXk8tPwBho?blocks=hide), which also pulls in data from our [Contracts AirTable](https://airtable.com/appbjBTRIbgRiElkr/tbliwB70vYg3hlkb1/viwWPJhcFbXUJZUO6?blocks=hide).

When built via Jupyter Book, all leads are anonymized.
If you want de-anonymized leads, run the notebook locally.

:::{admonition} To run this notebook locally
:class: dropdown
To see the visualizations locally, follow these steps:

1. Get an API key for AirTable (see [our team compass docs on AirTable](https://compass.2i2c.org/administration/airtable/)) and store it in an environment variable called `AIRTABLE_AP_KEY`.
2. Download the latest data:

   ```bash
   python book/scripts/download_airtable_data.py
   ```
3. Run this notebook from top to bottom.

There are several important fields in both {kbd}`Leads` and {kbd}`Contracts`, they're described below:

- {kbd}`Start Date` / {kbd}`End Date`: The starting and ending date of a contract.
- {kbd}`Amount`: The total budget amount in the grant.
- {kbd}`Amount for 2i2c`: The budget that is available to 2i2c (if <100% of the amount total)
- {kbd}`CSS %`: The % that CS&S will take for their indirect costs.
:::

:::{admonition} How numbers are prioritized
:class: dropdown
This notebook tries to use the _most accurate data that we've got_.
For example, contracts are usually more accurate than leads.
For data about dates and $$ amounts, here's the logic we follow:

1. {kbd}`2i2c Available $$`. If we have manually specified an amount for 2i2c, use this above all else.
2. {kbd}`Amount (from Contract)`. If we have a contract with CS&S for this Lead, use this.
3. {kbd}`Amount (from Leads)`. If we have no contract, use our Leads airtable for a best estimate.
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

twoc.set_plotly_defaults()

# This just suppresses a warning
pd.set_option("future.no_silent_downcasting", True)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Costs

Costs are manually calculated for now from [this Google Sheet](https://docs.google.com/spreadsheets/d/1OpKfPSIiFTY28OkV6--MhZygvdLVSdmpagjlnge2ELc/edit?usp=sharing). Monthly costs are calculated from the table below.
We'll define a baseline cost as the average over the last three months of this table.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
url = "https://docs.google.com/spreadsheets/d/1hhU67gNlrMgm5qrPGROQEktpxCUckQEQGDjTbPUU94U/export?format=xlsx"
costs = pd.read_excel(url, sheet_name="Cost modeling", header=0)
costs = costs[["Month", "Monthly cost (no FSP)", "Monthly cost (with FSP)"]]
costs.loc[:, "Month"] = pd.to_datetime(costs["Month"])
costs = costs.rename(columns={"Month": "Date"})
                     
# These costs *exclude* our fiscal sponsor fee.
# This is because all of the `leads` data subtracts the FSP fee in its amount
MONTHLY_COSTS = costs["Monthly cost (no FSP)"].tail(5).mean()
ANNUAL_COSTS = MONTHLY_COSTS * 12

md = f"""
- **Assumed annual costs (no FSP)**: ${ANNUAL_COSTS:,.0f}
- **Assumed monthly costs (no FSP)**: ${MONTHLY_COSTS:,.0f}
"""
Markdown(md)
# costs.tail()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Leads and contracts

**Leads** are a precursor to contracts. Each has a % probability of success, and revenue is generally _weighted_ by this chance. Leads follow this lifecycle:

:::{figure} ./images/leads_lifecycle.png
:width: 450px
The leads lifecycle, see [our Leads AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblmRU6U53i8o7z2I/viw8xzzSXk8tPwBho?blocks=hide) for the Leads data.
:::

**Contracts** are legal agreements with $$ attached to them, and their revenue is treated as 100% reliable.

**We include contracts data with our leads**: For any lead that has a contract, it is linked to a record in {kbd}`Contracts`. Our Leads AirTable has several linked fields from these records, so we have the relevant contract information for each lead.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Read in the latest data from AirTable.
# To update the data, run scripts/download_airtable_data.py
column_mappings = {
    # Unique name
    "Name": "Name",
    # Status of the lead
    "Status": "Status",
    # The total amount for 2i2c after subtracting the FSP fee
    "2i2c spendable amount": "Amount for 2i2c",
    # The chance that we'll get this award
    "% probability of success": "% success",
    # The start date of the contract or the lead depending on what's there
    "Start date (final)": "Start Date",
    # The end date of the contract or the lead depending on what's there
    "End date (final)": "End Date",
    # Grant vs. Contract
    "Contract Type": "Contract Type",
    # The type of service
    "Engagement Type": "Engagement Type",
}
leads = pd.read_csv("./data/airtable-leads.csv", usecols=column_mappings.keys())
leads = leads.rename(columns=column_mappings)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Read in latest fundraising data from AirTable
column_mappings = {
    # Unique name
    "Name": "Name",
    # Status of the lead
    "Status": "Status",
    # The total amount for 2i2c after subtracting the FSP fee
    "2i2c spendable amount": "Amount for 2i2c",
    # The chance that we'll get this award
    "% probability of success": "% success",
    # The start date of the contract or the lead depending on what's there
    "Start Date (final)": "Start Date",
    # The end date of the contract or the lead depending on what's there
    "End Date (final)": "End Date",
}
# TODO: BROKEN: The column names have changed and we must change them
# fundraising = pd.read_csv("./data/airtable-sales.csv", usecols=column_mappings.keys())
# fundraising = fundraising.rename(columns=column_mappings)

# # Quick clean up
# fundraising["Contract Type"] = "Core Funding"
# fundraising["Engagement Type"] = "Core Funding"
# fundraising = fundraising.replace({"Ask": "Prospect", "Cultivate": "Prospect"})
# fundraising = fundraising.query("`% success` > 0")
# fundraising["% success"] /= 100.
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# # Concatenate them so that we can analyze them together
# leads = pd.concat([leads, fundraising])

# # Anonymize leads if we are in a CI/CD environment because this will be public
# if "GITHUB_ACTION" in os.environ:
#     for ix, name in leads["Name"].items():
#         leads.loc[ix, "Name"] = f"Lead {ix}"

# leads.head().style.set_caption("Sample leads from our Leads AirTable.")
```

+++ {"editable": true, "slideshow": {"slide_type": ""}, "tags": ["remove-cell"]}

### Clean up our leads

The following cells clean up our leads data.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # Remove all lost leads
# leads = leads.query("Status != 'Lost'")

# # Remove any lead that:
# #   1. Misses information from the columns above
# #   2. Has an Amount for 2i2c that isn't > 0
# missing_amount_for_2i2c = ~leads.eval("`Amount for 2i2c` > 0")

# # Don't worry about the % success / issue columns in case they're missing
# missing_values = (
#     leads.drop(columns=["% success"]).isnull().apply(lambda a: any(a), axis=1)
# )
# leads_to_remove = missing_amount_for_2i2c | missing_values
# leads_to_remove = leads_to_remove[leads_to_remove == True].index
# leads_to_remove = leads.loc[leads_to_remove]

# # Drop all leads with missing information
# print(f"Dropping {len(leads_to_remove)} leads...")
# leads = leads.drop(leads_to_remove.index)

# # If we want to look at the leads that were dropped
# # ishow(leads_to_remove, pageLength=50)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # Consolidate multiple service types into one to simplify plotting
# rename_labels = {
#     "Hub: Special": "Hub service",
#     "Hub: Research": "Hub service",
#     "Hub: Education": "Hub service",
#     "Development": "Partnership",
# }
# leads = leads.replace(rename_labels)

# # Label leads as renewals vs. new contracts for better plotting
# for ix, irow in leads.iterrows():
#     # If it's awarded then skip it because we're only marking prospectives
#     if "Awarded" in irow["Status"]:
#         continue
#     if irow["Status"].lower() == "renewal":
#         leads.loc[ix, "Contract Type"] = "Projected renewal"
#         leads.loc[ix, "Engagement Type"] = "Projected renewal"
#     elif irow["Status"].lower() == "needs admin":
#         leads.loc[ix, "Contract Type"] = "Needs admin"
#         leads.loc[ix, "Engagement Type"] = "Needs admin"
#     elif irow["Engagement Type"].lower() == "core funding":
#         leads.loc[ix, "Contract Type"] = "Projected core funding"
#         leads.loc[ix, "Engagement Type"] = "Projected core funding"
#     else:
#         leads.loc[ix, "Contract Type"] = "Projected new contract"
#         leads.loc[ix, "Engagement Type"] = "Projected new contract"
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Expected total amounts

We add a column for the *weighted* total amount to account for the fact that the lead may not come through.
This helps us calculate the _total expected amount of revenue_:

`total expected amount` = `lead total amounts` * `probability of each lead`

or if you're a mathy person:

```{math}

E \left[ \sum(leads) \right] = \sum_{1}^{n\_leads} lead\_total * lead\_probability = \sum \left( E[leads] \right)

```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # If something was awarded, treat its weighted amount as 100% regardless of the number we had there
# for ix, irow in leads.iterrows():
#     if irow["% success"]:
#         if "Awarded" in irow["Status"]:
#             leads.loc[ix, "Amount (weighted)"] = irow["Amount for 2i2c"]
#         else:
#             leads.loc[ix, "Amount (weighted)"] = (
#                 irow["Amount for 2i2c"] * irow["% success"]
#             )
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

### Amortize leads across months

For each lead, we spread the total amount into equal monthly amounts over the total lifetime of the contract.
If it's a lead we use _anticipated_ start/stop/amount. If it's a contract we use the contract values.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # Convert date columns to DateTime objects
# date_cols = ["Start Date", "End Date"]
# for col in date_cols:
#     leads.loc[:, col] = pd.to_datetime(leads[col])
#     # Round any dates to the nearest month start.
#     # This controls for the fact that some dates are the 1st, others the 31st.
#     leads.loc[:, col] = leads[col].apply(lambda x: round_to_nearest_month(x))
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # Generate a month entry for each lead with its amortized monthly amount
# amortized_records = []

# for ix, irow in leads.iterrows():
#     # We *exclude* the month of the right-most date because we know it is always the 1st
#     # This is because of the month rounding we did above
#     dates = pd.date_range(
#         irow["Start Date"], irow["End Date"], freq="MS", inclusive="left"
#     )
#     n_months = len(dates)
#     for date in dates:
#         amortized_records.append(
#             {
#                 "Date": date,
#                 "Total amount": irow["Amount for 2i2c"],
#                 "Monthly amount": irow["Amount for 2i2c"] / n_months,
#                 "Monthly amount (weighted)": irow["Amount (weighted)"] / n_months,
#                 "Contract Type": irow["Contract Type"],
#                 "Engagement Type": irow["Engagement Type"],
#                 "Name": irow["Name"],
#                 "% success": irow["% success"],
#             }
#         )
# amortized_records = pd.DataFrame(amortized_records)

# # Drop all records before January 2022 since data is unreliable before then
# amortized_records = amortized_records.query("Date >= '2022-01-01'")
# amortized_records = amortized_records.sort_values("Monthly amount", ascending=False)
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Historical revenue and costs

First we show our historical revenue and costs to understand where each has trended over time.
This only includes **leads that have contracts**, no "potential" leads are included.

We display types of revenue in different colors.
Hover over each section to see more information about it.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# # Preparing figures for visualization
# legend_orientation = dict(
#     orientation="h",  # Horizontal orientation
#     yanchor="bottom",
#     y=1.02,
#     xanchor="center",
#     x=0.5,
# )


# def update_layout(fig):
#     fig.update_layout(
#         legend=legend_orientation,
#         legend_title_text="",
#         yaxis_title="",
#         xaxis_title="",
#     )


# def write_image(fig, path, fig_height=350):
#     """Write an image for a plotly figure to a path while applying common styling."""
#     # Create a new figure object
#     fig = Figure(fig)
#     # Update font size for print
#     fig.update_layout(
#         height=fig_height,
#         legend_font_size=10,
#         title=dict(
#             font=dict(
#                 size=12,
#             )
#         ),
#     )
#     path = Path(path)
#     if not path.parent.exists():
#         path.parent.mkdir(parents=True, exist_ok=True)
#     fig.write_image(path, scale=4)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# # Historical query for the last 18 months through the next 6 months
# today = datetime.datetime.today()
# date_past = round_to_nearest_month(today - datetime.timedelta(days=30 * 18))
# date_future = round_to_nearest_month(today + datetime.timedelta(days=30 * 6))

# # Query for date range
# qu_date = f"Date > '{date_past:%Y-%m-%d}' and Date < '{date_future:%Y-%m-%d}'"

# # Query to remove prospective entries
# prospect_values = set(ii for ii in leads["Engagement Type"] if "projected" in ii.lower())
# qu_prospect = "`Engagement Type` not in @prospect_values"

# # Colors that help with plotting
# colors = {
#     "Core funding": twoc.colors["bigblue"],
#     "Partnership": twoc.colors["mauve"],
#     "Hub service": twoc.colors["coral"],
#     "Needs admin": "#ffa8a9",
#     "Projected renewal": "grey",
#     "Projected core funding": "darkgrey",
#     "Projected new contract": "lightgrey",
# }

# # Generate the plot
# figservice = px.bar(
#     amortized_records.query(qu_date).query(qu_prospect),
#     x="Date",
#     y="Monthly amount",
#     color="Engagement Type",
#     category_orders={"Engagement Type": colors.keys()},
#     color_discrete_map=colors,
#     hover_data="Name",
#     title="Monthly Revenue by Type",
# )
# figservice.update_traces(marker_line_width=0.2)
# figservice.add_scatter(
#     x=costs.query(qu_date)["Date"],
#     y=costs.query(qu_date)["Monthly cost (no FSP)"],
#     mode="lines",
#     line_shape="hv",
#     line_width=4,
#     line_color="black",
#     name="Costs",
# )
# update_layout(figservice)
# write_image(figservice, "_build/images/service_type.png")
# figservice
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Budget projections

Now we project into the future by including our **potential leads** as well.
This tells us what revenue to expect in the coming year.

We include two figures:

1. Our **weighted projected revenue** where lead totals are weighted by their expected probability.
2. Our **best-case scenario total revenue** which reflects revenue if every lead is successful.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# # Query for three months into the past through 12 months into the future
# date_past = round_to_nearest_month(today - datetime.timedelta(days=30 * 3))
# date_future = round_to_nearest_month(today + datetime.timedelta(days=30 * 12))
# qu_date = f"Date >= '{date_past:%Y-%m-%d}' and Date <= '{date_future:%Y-%m-%d}'"

# for iname in ["Monthly amount (weighted)", "Monthly amount"]:
#     # Bar plot of revenue
#     data_plot = amortized_records.query(qu_date)
#     if iname == "Monthly amount":
#         # If we are using total amount, only use records with > 25% chance success
#         data_plot = data_plot.query("`% success` > .25")

#     figservice = px.bar(
#         data_plot,
#         x="Date",
#         y=iname,
#         color="Engagement Type",
#         category_orders={"Engagement Type": colors.keys()},
#         color_discrete_map=colors,
#         hover_name="Name",
#         hover_data={
#             "Monthly amount": ":$,.0f",
#             "Monthly amount (weighted)": ":$,.0f",
#             "Total amount": ":$,.0f",
#             "% success": ":%.0f",
#         },
#         title=(
#             "Monthly Revenue (weighted)"
#             if "weighted" in iname
#             else "Monthly Revenue if contracts over 50% chance are awarded"
#         ),
#     )
#     figservice.update_traces(marker_line_width=0.2)

#     # Dotted line plot of costs
#     figservice.add_scatter(
#         x=costs.query(qu_date)["Date"],
#         y=costs.query(qu_date)["Monthly cost (no FSP)"],
#         mode="lines",
#         line_shape="hv",
#         line_dash="dash",
#         line_width=4,
#         line_color="black",
#         name="Costs",
#     )
#     update_layout(figservice)
#     figservice.show()
```
