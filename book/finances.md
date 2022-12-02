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
---

# Accounting Analysis

This analyses two data streams that represent 2i2c's financial activity.[^1]
It is meant to be used for both financial analysis and projection, as well as defining a few KPIs for sustainability and efficiency.

[^1]: Inspired by [James' AirTable demo](https://github.com/2i2c-org/dashboard/blob/main/AirTableIntegration.ipynb).

```{admonition} Data source
[Accounting base in AirTable](https://airtable.com/appbjBTRIbgRiElkr) that contains data that we use in these analyses.
It is accessed programmatically via an API key.
See [these instructions to create an API key for yourself](https://support.airtable.com/docs/creating-a-read-only-api-key).
```

+++ {"tags": ["remove-cell"]}

## Connect with our base

First we'll connect with our AirTable base via the [pyairtable python package](https://github.com/gtalarico/pyairtable), which is a Python bridge to AirTable's API.
See [AirTable IDs docs](https://support.airtable.com/docs/understanding-airtable-ids) for more information about how AirTable bases are structured.

```{code-cell} ipython3
:tags: [remove-cell]

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
:tags: [remove-cell]

# Imports that we'll use later
import altair as alt
import pandas as pd
from IPython.display import Markdown
```

## Financial summary

Provides an overview of our costs, revenue, and burn rate.

Our financial summary is generated from CS&S's monthly accounting data dumps. It is less user-friendly than the AirTable data used to define revenue, but has complete cost information, and so we use it to define our own costs and the **Source of Truth** for our financial situation.

**What's in this data**. These contain every transaction that 2i2c has ever recorded with CS&S.

```{admonition} To update this Table with the latest data
:class: dropdown

- Go to the [2i2c Financial Statements folder with CS&S](https://drive.google.com/drive/folders/1vM_QX1J8GW5z8W5WemxhhVjcCS2kEovN?usp=share_link) (only accessible to CS&S and 2i2c admins)
- Open the latest financial statement (new ones are loaded each month)
- In the first tab (`Account Transactions`), copy **all of the records** (excluding header names and footer content). This usually starts on **Row 9**.
- Go to [the Accounting Transactions Table](https://airtable.com/appbjBTRIbgRiElkr/tblDKGQFU0iEIa5Qb)
- Select **all cells on the table** (`ctrl/cmd + A` as a shortcut)
- Paste all of the copied records into this table. From the top, it should look like nothing has changed, but there should now be new records at the bottom.
```

```{code-cell} ipython3
:tags: [remove-cell]

# All accounting data from CS&S
accounts = base.get_table("tblDKGQFU0iEIa5Qb")
records = accounts.all()
accounts = pd.DataFrame([r["fields"] for r in records])
accounts = accounts.rename(columns={"Debit": "Cost", "Credit": "Revenue"})
accounts["Date"] = pd.to_datetime(accounts["Date"])
```

```{code-cell} ipython3
:tags: [remove-cell]

CHART_WIDTH = 700
```

```{code-cell} ipython3
:tags: [remove-cell]

# Summary of costs and revenue based on the books
overall_summary = accounts.copy()[["Date", "Cost", "Revenue"]]

# Calculate the monthly net and cumulative remaining over time
overall_summary = overall_summary.resample("M", on="Date").agg("sum").reset_index()
overall_summary["Net"] = overall_summary["Revenue"] - overall_summary["Cost"]
overall_summary["Cumulative"] = overall_summary["Net"].cumsum()

# Flip cost so that it plots upside down
overall_summary["Cost"] = -1 * overall_summary["Cost"]

# Melt to long form for plotting
overall_summary = overall_summary.melt(id_vars="Date", var_name="Category")
```

```{code-cell} ipython3
:tags: [remove-input, remove-stderr, remove-stdout]

# Plot net revenue, cumulative, and trend for next 6 months
net = alt.Chart(overall_summary.replace({"Cumulative": "Cash on Hand"}), title="Financial Summary (reverse time)", width=75)
yformat = alt.Axis(format="$,f")
yscale = alt.Scale(domain=[-200000, 700000])
net_br = net.mark_bar().encode(
    y=alt.Y("value", scale=yscale, axis=yformat),
    x=alt.X("Category", sort=alt.Sort(["Revenue", "Cost", "Net", "Cash on Hand"])),
    column=alt.Column("yearmonth(Date):O", spacing=5),
    tooltip=["Category", "value"],
    color=alt.Color(
        "Category",
        scale=alt.Scale(
            domain=["Revenue", "Cost", "Net", "Cash on Hand"],
            range=["lightgreen", "red", "lightgrey", "grey"],
        ),
    ),
).interactive()

net_br
```

## Costs

Monthly costs broken down by major category.

Costs are generated from CS&S's monthly accounting data dumps (see above).

```{code-cell} ipython3
:tags: [remove-cell]

# Drop revenue rows
costs = accounts.query("Cost > 0").drop(columns=["Revenue"])

KEEP_COST_COLUMNS = ["Date", "Cost", "Category"]

# Datetime
costs["Date"] = pd.to_datetime(costs["Date"])

# Categories our costs for a rough idea
for ix, row in costs.iterrows():
    if "other expenses" in row["Account"].lower():
        # For other expenses take the more specific category
        kind = row["Account"].split(":", 1)[-1]
    # For now, we are lumping contractors and employees together
    # This will make it harder for people to identify salary levels
    # based just on this data.
    elif "professional fees" in row["Account"].lower():
        kind = "Personnel Costs"
    elif "Personnel Costs" in row["Account"]:
        kind = "Personnel Costs"
    else:
        # Otherwise just take the account section
        kind = row["Account"].split(":")[0].split(maxsplit=1)[-1]
    costs.loc[ix, "Category"] = kind

# Only keep the columns we want
costs = costs[KEEP_COST_COLUMNS]

# Add a category so we can compare
costs["Kind"] = "cost"
```

```{code-cell} ipython3
:tags: [remove-cell, remove-stderr]

# Group by month and aggregate by type
cost_by_type = (
    costs.groupby([pd.Grouper(key="Date", freq="1M"), "Category"])
    .sum()
    .reset_index()
    .query("Cost > 0")
    .sort_values("Cost")
)

# Add sorting values to categories
sorted_categories = (
    cost_by_type.groupby("Category").sum().sort_values("Cost").index.values
)
cost_by_type.loc[:, "Sort"] = cost_by_type["Category"].map(
    lambda a: sorted_categories.tolist().index(a)
)
```

```{code-cell} ipython3
:tags: [remove-input, remove-stderr]

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

## Revenue

Our revenue data is defined in [the `Invoices` AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblPn2utQBDEQomeq).
It is synced from the CS&S AirTable that contains _all invoices for 2i2c_.

**What's in this data**. Includes all **invoices** but does not contain some revenue and costs. Excludes payments to employees as well as grant-based payments.

```{admonition} To sync this Table with the latest data
:class: dropdown

- Click on the [`Invoices` table](https://airtable.com/appbjBTRIbgRiElkr/tblPn2utQBDEQomeq)
- Click on the downward caret (`v`)
- Click on `⚡Sync Now`
```

+++ {"tags": ["remove-cell"]}

### Load and process data

Load the CS&S invoice data from AirTable as a DataFrame.

```{code-cell} ipython3
:tags: [remove-cell]

# Revenue data from CS&S
invoices = base.get_table("tblkmferOITqS2vH8")
invoices = invoices.all()
invoices = pd.DataFrame([r["fields"] for r in invoices])

# Subset the revenue
revenue = invoices.query("Type == 'ACCREC' and Status in ['PAID', 'AUTHORISED']")
```

```{code-cell} ipython3
:tags: [remove-cell]

# Use DateTime
revenue.loc[:, "Date"] = revenue["Date"].map(pd.to_datetime)

# Convert dollars to numbers
numeric_cols = ["Amount"]
for col in numeric_cols:
    revenue.loc[:, col] = revenue[col].replace("[\$,]", "", regex=True).astype(float)

# Renaming for convenience
revenue = revenue.rename(columns={"Contract Type": "Category"})

# Add a category so we can compare
revenue.loc[:, "Kind"] = "revenue"
```

```{code-cell} ipython3
:tags: [remove-input, remove-stderr]

# Group by category and month
revenue_monthly = (
    revenue.groupby([pd.Grouper(key="Date", freq="1M"), "Category", "Contact", "Status"])
    .sum()
    .reset_index()
)
```

```{code-cell} ipython3
:tags: [remove-input, remove-stderr]

ch = alt.Chart(revenue_monthly, width=CHART_WIDTH, title="Monthly revenue by category")
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color="Category",
    tooltip=["Category", "Amount"],
).interactive()
bar
```

Same plots but with `grants` removed because they are quite high.

```{code-cell} ipython3
:tags: [remove-input, remove-stderr]

ch = alt.Chart(revenue_monthly.query("Category != 'Grant'"), width=CHART_WIDTH, title="Monthly revenue by category (no grants)")
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color="Category",
    tooltip=["Category", "Amount"],
).interactive()
bar
```

**Hub Service revenue** with a monthly average

```{code-cell} ipython3
:tags: [remove-cell]

# Calculate a rolling mean each month
monthly_service_revenue = revenue_monthly.query("Category == 'Hub Service'")
revenue_monthly_totals = monthly_service_revenue.resample("M", on="Date").sum()
revenue_monthly_totals_means = revenue_monthly_totals.rolling(3, 1).mean().reset_index()
revenue_monthly_totals_means["Date"] = pd.to_datetime(revenue_monthly_totals_means["Date"])

# Remove the last month because it usually isn't yet updated with full data
revenue_monthly_totals_means = revenue_monthly_totals_means.iloc[:-1]
```

```{code-cell} ipython3
:tags: [remove-input]

# Print out an average amount
Markdown(
    f"3-month average revenue from hub service and development: **${revenue_monthly_totals_means.iloc[-3:]['Amount'].mean():,.2f}**"
)
```

```{code-cell} ipython3
:tags: [remove-input]

ch = alt.Chart(monthly_service_revenue, width=CHART_WIDTH, title="Monthly Hub Service Revenue with 3 month average")
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color=alt.Color("Status", scale=alt.Scale(range=["grey", "lightgreen"])),
    tooltip=["Category", "Amount"],
).interactive()

ch = alt.Chart(
    revenue_monthly_totals_means, width=CHART_WIDTH,
)
line = ch.mark_line(color="black").encode(
    x="yearmonth(Date):O",
    y="Amount",
)
scatter = ch.mark_point(color="black").encode(
    x="yearmonth(Date):O",
    y="Amount",
    tooltip=alt.Tooltip("Amount", format="$,.2f"),
).interactive()

bar + line + scatter
```

+++ {"tags": ["remove-cell"]}

Broken down by anonymized paying community

> **Note** The below cell is removed to avoid concerns about anonymity. We should define a policy about how / when we make the identity of our partner communities public.

```{code-cell} ipython3
:tags: [remove-cell]

# FLAGS
ANONYMIZE_NAMES = True

# Group by month and payer ID to plot
unique_names = revenue_monthly["Contact"].unique()
sorted_names = (
    revenue_monthly.groupby("Contact")
    .sum("Amount")
    .sort_values("Amount", ascending=False)
    .index.values
)
replacement_names = {
    name: f"Community partner {ii:2d}"
    for name, ii in zip(sorted_names, range(1, len(sorted_names) + 1))
}

if ANONYMIZE_NAMES:
    use_data = revenue_monthly.replace(replacement_names)
    use_names = list(replacement_names.values())
else:
    use_data = revenue_monthly
    use_names = sorted_names
    
# Only display the hub service since others are one-offs
use_data = use_data.query("Category == 'Hub Service'")

ch = alt.Chart(
    use_data,
    width=CHART_WIDTH,
    title="Monthly revenue by payer",
)
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color=alt.Color(
        "Contact:O",
        scale=alt.Scale(scheme="rainbow"),
        sort=use_names,
    ),
    order="Contact:Q",
    tooltip=["Contact", "Amount"]
).interactive()
bar
```

## Accounting tables

Summary tables of revenue and cost by major category.
Note that these are **reversed in time**.
They begin with the latest updated month and end with our earliest month.

```{code-cell} ipython3
:tags: [remove-cell]

def split_accounting_category(df):
    for ix, irow in df.iterrows():
        parts = irow["Account"].split(" ", 1)[-1].split(":", 1)
        if len(parts) == 1:
            parts = ["Misc"] + parts
        df.loc[ix, "Category"] = parts[0]
        df.loc[ix, "Child"] = parts[1]
    return df
    
def visualize_df_with_sum(df, summary=True):
    if summary is True:
        # Add summary statistics
        df.loc["Sum", :] = df.sum(0).values
        style = df.style

        # Highlight our summary rows
        def highlight_summaries(row):
            total_style = pd.Series("font-weight: bold;", index=["Sum"])
            return total_style
        style = style.apply(highlight_summaries, axis=0)
    else:
        style = df.style
    # Dollar formatting
    style = style.format("${:,.0f}", na_rep="$0")
    style = style.format_index("{:%B, %Y}", axis=1)

    return style
```

### Overview

```{code-cell} ipython3
:tags: [remove-input]

overall_summary_table = overall_summary.pivot(index="Category", values="value", columns="Date").sort_index(axis=1, ascending=False).loc[["Revenue", "Cost", "Net", "Cumulative"]]
overall_summary_table = overall_summary_table.rename(index={"Cumulative": "Cash on Hand (end of month)"})
visualize_df_with_sum(overall_summary_table, summary=False)
```

### Cost

```{code-cell} ipython3
:tags: [remove-input]

# Group by month
costs_summary = costs.groupby(["Category"]).resample("M", on="Date").sum("Cost")["Cost"]

# Unstack date
costs_summary = costs_summary.unstack("Date")

# Sort from least to most expensive and then by category
costs_summary = costs_summary.loc[costs_summary.sum(1).sort_values().index]
costs_summary = costs_summary.sort_index()
costs_summary = costs_summary.sort_index(axis=1, ascending=False)

visualize_df_with_sum(costs_summary)
```

### Revenue

```{code-cell} ipython3
:tags: [remove-input]

# Sum by category and unstack
revenue_summary = revenue_monthly.groupby(["Date", "Category"]).sum("Amount Paid").loc[:, "Amount Paid"].unstack("Date")

# Only show the months that we have accounting information for
# This way we know it's had time to be updated
revenue_summary = revenue_summary.sort_index(axis=1, ascending=False)
revenue_summary = revenue_summary.loc[:, costs_summary.columns[0]:]

visualize_df_with_sum(revenue_summary)
```
