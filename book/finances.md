---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.15.2
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

+++ {"user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

# Accounting and finance

This page summarizes 2i2c's financial picture, as well as our major cost and revenue trends.[^1]
Its goal is to provide transparency about how money is flowing through our organization.

```{admonition} This data is not currently reliable
We've learned from CS&S that their AirTable accounting data is not reliable enough to use here.
We'll update this once we learn more.
```

Last updated: **{sub-ref}`today`**

[^1]: Inspired by [James' AirTable demo](https://github.com/2i2c-org/dashboard/blob/main/AirTableIntegration.ipynb).

(data-sources)=
```{admonition} Data sources
:class: dropdown

There are two data sources on this page, both of them are AirTable tables that are synced from CS&S data:

- **Accounting tables** are documented at {external:doc}`on our Accounting sources page <finance/accounting>`.
- **Invoicing data** are documented at {external:doc}`on our Invoices and Contracts page <finance/contracts>`.

```

+++ {"tags": ["remove-cell"], "user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

## Connect with our base

First we'll connect with our AirTable base via the [pyairtable python package](https://github.com/gtalarico/pyairtable), which is a Python bridge to AirTable's API.
See [AirTable IDs docs](https://support.airtable.com/docs/understanding-airtable-ids) for more information about how AirTable bases are structured.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Assume the API key is stored as an environment variable
import os

from pyairtable import Base, Table

if "AIRTABLE_API_KEY" not in os.environ:
    raise ValueError("Environment variable AIRTABLE_API_KEY not defined")
api_key = os.environ["AIRTABLE_API_KEY"]   

# Base ID for `Accounting`: https://airtable.com/appbjBTRIbgRiElkr
base_id = "appbjBTRIbgRiElkr"
base = Base(api_key, base_id)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Imports that we'll use later
import altair as alt
import pandas as pd
from IPython.display import Markdown, display
```

+++ {"user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

## Summary of cost and revenue

This provides a high-level overview of our revenue and expenses over time.
Months with a large influx of cash correspond to new grants that we have received, that are generally paid in batch amounts.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Start date for the records we'll display
from datetime import datetime, timedelta

# Using 7 months because the latest month tends to be not up to date
# So this gives us N=6 months + 1 for the latest month.
n_months = 7
start_date = datetime.today() - timedelta(days=30*n_months)
start_date = datetime(year=start_date.year, month=start_date.month, day=1)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# All accounting data from CS&S
accounts = base.table("tblDKGQFU0iEIa5Qb")
records = accounts.all()
accounts = pd.DataFrame([r["fields"] for r in records])
accounts = accounts.rename(columns={"Debit": "Cost", "Credit": "Revenue"})
accounts["Date"] = pd.to_datetime(accounts["Date"])

# Only keep data within the last N months
accounts = accounts.query("Date > @start_date")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Renames
accounts = accounts.rename(columns={"Net": "Amount", "Category without number": "Category"})

# Re-categorize our old AWS and Google Cloud entries that were created before the "rebillable to customers" category existed
cloud_charge_keywords = ["google cloud", "google*cloud", "cloud infrastructure", "aws", "amazong web services", "azure"]
old_category = "Professional Fees/Outside Svcs.:Information Technology Services"
for kw in cloud_charge_keywords:
    cloud_matches = accounts["Description"].str.lower().str.contains(kw.lower())
    incorrectly_categorized = accounts["Category"].str.contains(old_category)
    matches = (cloud_matches + incorrectly_categorized) > 0
    accounts.loc[matches, "Category"] = "Costs Rebillable to Customers"
    

# Split out cloud costs because we treat these costs differently from other costs
# This is because we recover them through invoices, and the total should be zero
rebillable = accounts.query("Category == 'Costs Rebillable to Customers'").copy()
accounts = accounts.query("Category != 'Costs Rebillable to Customers'").copy()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
CHART_WIDTH = 575
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Summary of costs and revenue based on the books
overall_summary = accounts.copy()[["Date", "Cost", "Revenue"]]

# Calculate the monthly net and cumulative remaining over time
overall_summary = overall_summary.resample("M", on="Date").agg("sum").reset_index()
overall_summary["Net"] = overall_summary["Revenue"] - overall_summary["Cost"]

# Melt to long form for plotting
overall_summary = overall_summary.melt(id_vars="Date", var_name="Category")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
category_plots = ["Revenue", "Cost", "Net"]
category_colors = ["lightgreen", "red", "grey"]

alt.Chart(overall_summary, title=f"Monthly costs, revenue, and net", width=75).mark_bar().encode(
    y=alt.Y("value"),
    x=alt.X("Category", scale=alt.Scale(domain=category_plots)),
    column=alt.Column("yearmonth(Date):O"),
    color=alt.Color(
        "Category",
        scale=alt.Scale(
            domain=category_plots,
            range=category_colors,
        ),
    ),
    tooltip=["Category", "value"],
).interactive()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
perc_calculate = overall_summary.set_index("Date")
overall_revenue_as_perc_of_costs =  perc_calculate.query("Category == 'Revenue'")["value"] / perc_calculate.query("Category == 'Cost'")["value"]
overall_revenue_as_perc_of_costs_mean = overall_revenue_as_perc_of_costs.mean()
chart = alt.Chart(overall_revenue_as_perc_of_costs.reset_index(), width=CHART_WIDTH, title="Percent costs recovered with revenue (6 month average in red)").mark_bar(width=50).encode(
    x="yearmonth(Date):O",
    y=alt.Y(
        "value",
        scale=alt.Scale(domain=[0, 2]),
        axis=alt.Axis(format='%')
    ),
    tooltip=["Date", "value"],
).interactive()

one_hundred = alt.Chart(pd.DataFrame({'y': [1]})).mark_rule().encode(y='y')
cost_recovery_mean = alt.Chart(
    pd.DataFrame({'y': [overall_revenue_as_perc_of_costs_mean]})).mark_rule(strokeDash=[8,4], color="red").encode(y='y')
chart + one_hundred + cost_recovery_mean
```

+++ {"user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

## Costs

Monthly costs are based on accounting transactions, and broken down by major category.

Costs are generated from CS&S's monthly accounting data dumps (see [data sources](#data-sources)).

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Drop revenue rows
costs = accounts.query("Cost > 0").drop(columns=["Revenue"])

KEEP_COST_COLUMNS = ["Date", "Cost", "Category"]

# Datetime
costs["Date"] = pd.to_datetime(costs["Date"])

# Categories our costs for a rough idea
for ix, row in costs.iterrows():
    if "other expenses" in row["Category"].lower():
        # For other expenses take the more specific category
        kind = row["Category"].split(":", 1)[-1]
    # For now, we are lumping contractors and employees together
    # This will make it harder for people to identify salary levels
    # based just on this data.
    elif "professional fees" in row["Category"].lower():
        kind = "Personnel Costs"
    elif "Personnel Costs" in row["Category"]:
        kind = "Personnel Costs"
    elif "Program Expenses" in row["Category"]:
        kind = "Grants to Other Organizations"
    else:
        # Otherwise just take the account section
        kind = row["Category"].split(":")[0]
    costs.loc[ix, "Category"] = kind

# Only keep the columns we want
costs = costs[KEEP_COST_COLUMNS]

# Add a category so we can compare
costs["Kind"] = "cost"
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell, remove-stderr]
---
# Group by month and aggregate by type
cost_by_type = (
    costs.groupby([pd.Grouper(key="Date", freq="1M"), "Category"])
    .sum(numeric_only=True)
    .reset_index()
    .query("Cost > 0")
    .sort_values("Cost")
)

# Add sorting values to categories
sorted_categories = (
    cost_by_type.groupby("Category").sum(numeric_only=True).sort_values("Cost").index.values
)
cost_by_type.loc[:, "Sort"] = cost_by_type["Category"].map(
    lambda a: sorted_categories.tolist().index(a)
)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Exclude a few categories that aren't representative of our spending
# These do incur a real cost, but aren't helpful in knowing where our money goes
# However we should make sure this doesn't skew our perception of our *income*
# because some of that income does get drained by these costs.
# This is why our total cash on hand doesn't exclude these categories, only this viz
exclude_cost_categories = [
    "Grants to Other CS&S FSPs",
    "Grants to Other Organizations",
]
cost_by_type = cost_by_type.query("Category not in @exclude_cost_categories")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr]
---
ch = alt.Chart(cost_by_type, width=CHART_WIDTH, title="Monthly spending by category")
ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y=alt.Y(
        "Cost",
        axis=alt.Axis(
            format="$,f",
        ),
    ),
    color="Category",
    tooltip=["Category", "Cost"],
).interactive()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr]
---
by_date = cost_by_type.set_index(["Date", "Category"])["Cost"].unstack("Category")
by_date_percentage = by_date.apply(lambda a: a / a.sum(), axis=1)
by_date_percentage = by_date_percentage.stack("Category").reset_index(name="Percent")

ch = alt.Chart(by_date_percentage, width=CHART_WIDTH, title="Monthly spending by category")
ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y=alt.Y(
        "Percent",
        scale=alt.Scale(domain=[0, 1]),
        axis=alt.Axis(format='%')
    ),
    color="Category",
    tooltip=["Category", "Percent"],
).interactive()
```

+++ {"user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

## Revenue

Revenue is based on monthly invoicing data.
See [data sources](#data-sources) for background on where this data comes from.

+++ {"tags": ["remove-cell"], "user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

### Load and process data

Load the CS&S invoice data from AirTable as a DataFrame.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Revenue data from CS&S
invoices = base.table("tblkmferOITqS2vH8")
invoices = invoices.all()
invoices = pd.DataFrame([r["fields"] for r in invoices])

# Subset the revenue
revenue = invoices.query("Type == 'ACCREC' and Status in ['PAID', 'AUTHORISED']").copy()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Use DateTime
revenue.loc[:, "Date"] = revenue["Date"].map(pd.to_datetime)

# Only keep the latest months (see comments on accounts variable for explanation)
revenue = revenue.query("Date > @start_date").copy()

# Drop missing values
revenue = revenue.dropna()

# Convert dollars to numbers
numeric_cols = ["Amount"]
for col in numeric_cols:
    revenue.loc[:, col] = revenue[col].replace("[\$,]", "", regex=True).astype(float)

# Renaming for convenience
revenue = revenue.rename(columns={"Service Type (from Contracts)": "Category"})
revenue.loc[:, "Category"] = revenue["Category"].map(lambda a: a[0])

# Add a category so we can compare
revenue.loc[:, "Kind"] = "revenue"
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr]
---
# Group by category and month
revenue_monthly = (
    revenue.groupby([pd.Grouper(key="Date", freq="1M"), "Category", "Contact", "Status"])
    .sum()
    .reset_index()
)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr]
---
# Sum the revenue within each category
ch = alt.Chart(revenue_monthly, width=CHART_WIDTH, title="Monthly revenue by category")
bar1 = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color="Category",
    tooltip=["Category", "Amount"],
).interactive()
display(bar1)

# Count the number of invoices within each category
ch = alt.Chart(revenue_monthly, width=CHART_WIDTH, title="Number of invoices by category")
bar2 = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="count(Contact)",
    color="Category",
    tooltip=["Category", "count(Contact)"],
).interactive()
display(bar2)
```

+++ {"user_expressions": [], "editable": true, "slideshow": {"slide_type": ""}}

Same revenue plot as above, but with `grants` removed because they skew the visualizations.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, remove-stderr]
---
revenue_monthly_nogrants = revenue_monthly.loc[~revenue_monthly["Category"].str.contains("Grant")]
ch = alt.Chart(revenue_monthly_nogrants, width=CHART_WIDTH, title="Monthly revenue by category (no grants)")
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color="Category",
    tooltip=["Category", "Amount"],
).interactive()
bar
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
---

```
