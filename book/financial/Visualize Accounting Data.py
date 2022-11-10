# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Accounting Analysis
#
# Inspired by [James' AirTable demo](https://github.com/2i2c-org/dashboard/blob/main/AirTableIntegration.ipynb).
#
# This analyses two data streams that represent 2i2c's financial activity.
# It is meant to be used for both financial analysis and projection, as well as defining a few KPIs for sustainability and efficiency.
#
# See [the kpis repository](https://github.com/2i2c-org/kpis) for more information.
#
# We have [an Accounting base in AirTable](https://airtable.com/appbjBTRIbgRiElkr) that contains data that we use in these analyses.
# It is accessed programmatically via an API key.
# See [these instructions to create an API key for yourself](https://support.airtable.com/docs/creating-a-read-only-api-key).

# + [markdown] tags=["remove-cell"]
# ## Connect with our base
#
# First we'll connect with our AirTable base via the [pyairtable python package](https://github.com/gtalarico/pyairtable), which is a Python bridge to AirTable's API.
# See [AirTable IDs docs](https://support.airtable.com/docs/understanding-airtable-ids) for more information about how AirTable bases are structured.

# + tags=["remove-cell"]
# Assume the API key is stored as an environment variable
import os

from pyairtable import Base, Table

try:
    api_key = os.environ["AIRTABLE_API_KEY"]
except:
    print("Environment variable AIRTABLE_API_KEY not defined")

# Base ID for `Accounting`: https://airtable.com/appbjBTRIbgRiElkr
base_id = "appbjBTRIbgRiElkr"
base = Base(api_key, base_id)

# + tags=["remove-cell"]
# Imports that we'll use later
import altair as alt
import pandas as pd
from IPython.display import Markdown
# -

# ## Financial summary
#
# Provides an overview of our costs, revenue, and burn rate.
#
# Our financial summary is generated from CS&S's monthly accounting data dumps. It is less user-friendly than the AirTable data used to define revenue, but has complete cost information, and so we use it to define our own costs and the **Source of Truth** for our financial situation.
#
# **What's in this data**. These contain every transaction that 2i2c has ever recorded with CS&S.
#
# ```{admonition} To update this Table with the latest data
# :class: dropdown
#
# - Go to the [2i2c Financial Statements folder with CS&S](https://drive.google.com/drive/folders/1vM_QX1J8GW5z8W5WemxhhVjcCS2kEovN?usp=share_link) (only accessible to CS&S and 2i2c admins)
# - Open the latest financial statement (new ones are loaded each month)
# - In the first tab (`Account Transactions`), copy **all of the records** (excluding header names and footer content). This usually starts on **Row 9**.
# - Go to [the Accounting Transactions Table](https://airtable.com/appbjBTRIbgRiElkr/tblDKGQFU0iEIa5Qb)
# - Select **all cells on the table** (`ctrl/cmd + A` as a shortcut)
# - Paste all of the copied records into this table. From the top, it should look like nothing has changed, but there should now be new records at the bottom.
# ```

# + tags=["remove-cell"]
# All accounting data from CS&S
accounts = base.get_table("tblDKGQFU0iEIa5Qb")
records = accounts.all()
accounts = pd.DataFrame([r["fields"] for r in records])
accounts = accounts.rename(columns={"Debit": "Cost", "Credit": "Revenue"})
accounts["Date"] = pd.to_datetime(accounts["Date"])


# + tags=["remove-cell"]
# Summary of costs and revenue based on the books
summary = accounts.copy()[["Date", "Cost", "Revenue"]]

# Calculate the monthly net and cumulative remaining over time
summary = summary.resample("M", on="Date").agg("sum").reset_index()
summary["Net"] = summary["Revenue"] - summary["Cost"]
summary["Cumulative"] = summary["Net"].cumsum()

# Flip cost so that it plots upside down
summary["Cost"] = -1 * summary["Cost"]

# Melt to long form for plotting
summary = summary.melt(id_vars="Date", var_name="Category")

# Save burn rate for future comparison
burn_rate = summary.query("Category == 'Net'")

# + tags=["remove-cell"]
CHART_WIDTH = 700

# + tags=["remove-input"]
latest_summary = summary.set_index("Date")
latest_summary = latest_summary.loc[latest_summary.index.max()].replace("Cumulative", "Cash on Hand")
max_date = latest_summary.index[0]
md = f"Statistics for month: **{max_date:%Y-%m-%d}**\n\n"

for _, irow in latest_summary.iterrows():
    md += f"- **{irow['Category']}**: \${irow['value']:,.0f}\n"
Markdown(md)

# + tags=["remove-input", "remove-stderr"]
# Plot net revenue, cumulative, and trend for next 6 months
net = alt.Chart(summary.replace({"Cumulative": "Cash on Hand"}), title="Financial Summary", width=75)
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

# + tags=["remove-input", "remove-stderr"]
# Calculates our number of months cash remaining given our burn rate
burn_rate = summary.query("Category in ['Net', 'Cumulative']").pivot(
    index="Date", columns="Category", values="value"
)
burn_rate["Net 6mo Median"] = burn_rate["Net"].rolling(6).median()
burn_rate["Months Remaining"] = burn_rate["Cumulative"] / (
    -1 * burn_rate["Net 6mo Median"]
)

months = (
    alt.Chart(
        burn_rate["Months Remaining"].reset_index(),
        width=1050,
        title="Cash runway (months)",
    )
    .mark_line()
    .encode(x="Date", y=alt.Y("Months Remaining", scale=alt.Scale(domain=(0, 24))))
)
line = (
    alt.Chart(pd.DataFrame({"y": [6]}))
    .mark_rule(strokeDash=[10, 10])
    .encode(y=alt.Y("y"))
)

months + line
# -

# ## Costs
#
# Monthly costs broken down by major category.
#
# Costs are generated from CS&S's monthly accounting data dumps (see above).

# + tags=["remove-cell"]
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
    elif "professional fees" in row["Account"].lower():
        kind = "Personnel Costs"
    else:
        # Otherwise just take the account section
        kind = row["Account"].split(":")[0].split(maxsplit=1)[-1]
    costs.loc[ix, "Category"] = kind

# Only keep the columns we want
costs = costs[KEEP_COST_COLUMNS]

# Add a category so we can compare
costs["Kind"] = "cost"

# + tags=["remove-cell", "remove-stderr"]
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

# + tags=["remove-input", "remove-stderr"]
ch = alt.Chart(cost_by_type, width=CHART_WIDTH)
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
# -

# ## Revenue
#
# Our revenue data is defined in [the `Invoices` AirTable](https://airtable.com/appbjBTRIbgRiElkr/tblPn2utQBDEQomeq).
# It is synced from the CS&S AirTable that contains _all invoices for 2i2c_.
#
# **What's in this data**. Includes all **invoices** but does not contain some revenue and costs. Excludes payments to employees as well as grant-based payments.
#
# ```{admonition} To sync this Table with the latest data
# :class: dropdown
#
# - Click on the [`Invoices` table](https://airtable.com/appbjBTRIbgRiElkr/tblPn2utQBDEQomeq)
# - Click on the downward caret (`v`)
# - Click on `⚡Sync Now`
# ```

# + [markdown] tags=["remove-cell"]
# ### Load and process data
#
# Load the CS&S invoice data from AirTable as a DataFrame.

# + tags=["remove-cell"]
# Revenue data from CS&S
invoices = base.get_table("tblkmferOITqS2vH8")
invoices = invoices.all()
invoices = pd.DataFrame([r["fields"] for r in invoices])

# Subset the revenue
revenue = invoices.query("Type == 'ACCREC' and Status == 'PAID'")

# + tags=["remove-cell"]
# Use DateTime
revenue["Date"] = revenue["Date"].map(pd.to_datetime)

# Convert dollars to numbers
numeric_cols = ["Amount"]
for col in numeric_cols:
    revenue[col] = revenue[col].replace("[\$,]", "", regex=True).astype(float)

# Iterate through records to make a bunch of row-specific changes
for ix, row in revenue.iterrows():
    # Categorize as grant, development, or service revenue
    if row["Restricted Fund"] == "2i2c: General":
        # We are a service contract of some kind
        if "GESIS" in row["Contact"]:
            kind = "Development"
        else:
            kind = "Hub service"
    else:
        kind = "Grant"

    revenue.loc[ix, "Category"] = kind

# Add a category so we can compare
revenue["Kind"] = "revenue"

# + tags=["remove-input", "remove-stderr"]
# Group by category and month
revenue_monthly = (
    revenue.groupby([pd.Grouper(key="Date", freq="1M"), "Category", "Contact"])
    .sum()
    .reset_index()
)

# Only keep contracts so that we visualize contract revenue growth
revenue_monthly = revenue_monthly.query("Category != 'Grant'")

# Calculate a rolling mean each month
revenue_monthly_totals = revenue_monthly.resample("M", on="Date").sum()
revenue_monthly_totals_means = revenue_monthly_totals.rolling(3, 1).mean().reset_index()

# Print out an average amount
Markdown(
    f"3-month average revenue from hub service and development: **${revenue_monthly_totals_means.iloc[-3:]['Amount'].mean():,.2f}**"
)

# + tags=["remove-input", "remove-stderr"]
ch = alt.Chart(revenue_monthly, width=CHART_WIDTH, title="Monthly revenue by category (with 3-month average)")
bar = ch.mark_bar().encode(
    x="yearmonth(Date):O",
    y="Amount",
    color="Category",
)

ch = alt.Chart(
    revenue_monthly_totals_means, width=CHART_WIDTH, title="Monthly revenue by category"
)
line = ch.mark_line(color="black").encode(
    x="yearmonth(Date):O",
    y="Amount",
)

bar + line
# -

# Broken down by anonymized paying institution

# + tags=["remove-input", "remove-stderr"]
unique_names = revenue_monthly["Contact"].unique()
sorted_names = (
    revenue_monthly.groupby("Contact")
    .sum("Amount")
    .sort_values("Amount", ascending=False)
    .index.values
)
replacement_names = {
    name: f"Institution {ii:2d}"
    for name, ii in zip(sorted_names, range(1, len(sorted_names) + 1))
}

ANONYMIZE_NAMES = True
if ANONYMIZE_NAMES:
    use_data = revenue_monthly.replace(replacement_names)
    use_names = list(replacement_names.values())
else:
    use_data = revenue_monthly
    use_names = sorted_names

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
