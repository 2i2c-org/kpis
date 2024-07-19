# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import pandas as pd
import plotly_express as px
import numpy as np
from plotly.subplots import make_subplots
from twoc import colors as twocolors
from IPython.display import Markdown


# %%
# Hard-coded variables
ANNUAL_COSTS = 2200000
MONTHLY_COSTS = ANNUAL_COSTS / 12

# %% [markdown] user_expressions=[{"expression": "f\"${MONTHLY_COSTS:.0f}\"", "result": {"status": "ok", "data": {"text/plain": "'$183333'"}, "metadata": {}}}]
# Assumed monthly costs: {eval}`f"${MONTHLY_COSTS:.0f}"`

# %%
contracts = pd.read_csv("./data/airtable-contracts.csv")
leads = pd.read_csv("./data/airtable-leads.csv", index_col=0)
date_cols = ["Start Date", "End Date"]

# Drop items w/o start and end dates, and inactive contracts
contracts = contracts.dropna(subset=date_cols).reset_index()
leads = leads.dropna(subset=date_cols).reset_index()

for col in date_cols:
    contracts.loc[:, col] = pd.to_datetime(contracts[col])

for col in date_cols:
    if col in leads.columns:
        leads.loc[:, col] = pd.to_datetime(leads[col])


# %%
# Prep leads dataframe with `Lead` Contract type so we can add it to our amortized DF
for (rule, name) in [("== 'Renewal'", "Projected renewal"), ("!= 'Renewal'", "Projected new contract")]:
    for col in ["Contract Type", "Service Type"]:
        leads.loc[leads.eval("Status %s" % rule), col] = name

# Assume that all $$ in a lead is for 2i2c for now
leads = leads.rename(columns={"Expected total budget": "Amount for 2i2c"})
leads = leads.loc[leads["Amount for 2i2c"] > 0]

# Drop any leads that ended in the past or that already have a working contracts
# Because these leads are already recorded in contracts
awarded = leads["Contract Status"].str.contains("Awarded")
awarded = awarded.replace(np.nan, False)
leads = leads.loc[~awarded]

# Add leads to our contracts for future processing
records = pd.concat([contracts, leads])

# %% [markdown]
# For each contract, generate an amortized monthly amount between the start and end dates

# %%
amortized_records = []

for ix, irow in records.iterrows():
    dates = pd.date_range(irow["Start Date"], irow["End Date"], freq="MS")
    for date in dates:
        n_months = len(dates)
        monthly_amount_for_2i2c = irow["Amount for 2i2c"] / n_months
        amortized_records.append(
            {
                "Date": date,
                 "Monthly amount": monthly_amount_for_2i2c,
                 "Contract Type": irow["Contract Type"],
                 "Service Type": irow["Service Type"],
                 "Name": irow["Name"]
            }
        )
amortized_records = pd.DataFrame(amortized_records)
# Drop all records before January 2022 since data is unreliable before then
amortized_records = amortized_records.query("Date >= '2022-01-01'")
amortized_records = amortized_records.sort_values("Monthly amount", ascending=False)

# %% [markdown]
# Costs

# %% [markdown]
# Grants vs. contracts

# %%
FIGURE_HEIGHT = 350
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
        legend_title_text = "",
        legend_font_size = 10,
        yaxis_title = "",
        xaxis_title = "",
        height=FIGURE_HEIGHT,
        title=dict(
            font=dict(
                size=12,
            )
        )
    )


# %%
qu_historical = "Date < '2024-10-01' and `Contract Type` not in  ['Projected new contract', 'Projected renewal']"
figcontract = px.bar(amortized_records.query(qu_historical), x="Date", y="Monthly amount", color="Contract Type",
        hover_data="Name", title="Monthly Revenue by Contract Type")
figcontract.update_traces(marker_line_width=0)
update_layout(figcontract)
figcontract.write_image("/Users/choldgraf/Downloads/contract_type.png", scale=4)
figcontract

# %% [markdown]
# Service type

# %%
url = 'https://docs.google.com/spreadsheets/d/1OpKfPSIiFTY28OkV6--MhZygvdLVSdmpagjlnge2ELc/export?format=xlsx'
costs = pd.read_excel(url, sheet_name="Cost modeling")
costs = costs[["Month", "Monthly cost"]]
costs.loc[:, "Month"] = pd.to_datetime(costs["Month"])

# %%
colors = {
    "Core support": twocolors["bigblue"],
    "Hub service": twocolors["coral"],
    "Development": twocolors["pink"],
    "Projected renewal": "darkgrey",
    "Projected new contract": "lightgrey",
}
figservice = px.bar(amortized_records.query(qu_historical), x="Date", y="Monthly amount", color="Service Type",
        category_orders={"Service Type": colors.keys()}, color_discrete_map=colors, hover_data="Name", title="Monthly Revenue by Type")
figservice.update_traces(marker_line_width=.2)
figservice.add_scatter(x=costs["Month"], y=costs["Monthly cost"], line_shape="hv", line_width=4, line_color="black", name="Costs")
update_layout(figservice)
figservice.write_image("/Users/choldgraf/Downloads/service_type.png", scale=4)
figservice

# %% [markdown]
# Last 4 months

# %%
# Sum all by service type for smoother plots but without interactivity
by_service_type = amortized_records.groupby(["Date", "Service Type"]).sum("Monthly amount").reset_index()

# %%
qu_future = "Date > '2024-04-01' and Date < '2025-02-01'"
for idata, iname in [(amortized_records, "Name"), (by_service_type, "Service Type")]:
    figservice = px.bar(
        idata.query(qu_future), x="Date", y="Monthly amount", color="Service Type",
        category_orders={"Service Type": colors.keys()}, color_discrete_map=colors, hover_data=iname, height=300, title="Monthly Projected Revenue by Service Type")
    # No lines between contracts so it doesn't confuse things
    figservice.update_traces(marker_line_width=.2)
    figservice.add_hline(MONTHLY_COSTS, line_dash="dash", line_color=twocolors["coral"])
    update_layout(figservice)
    figservice.show()

# %% [markdown]
# New revenue by month

# %%
contracts["Start Date"] = pd.to_datetime(contracts["Start Date"])
contracts_monthly = contracts.query("`Start Date` < '2024-07-01'").resample("ME", on="Start Date").sum("Amount for 2i2c").reset_index()
px.bar(contracts_monthly, x="Start Date", y="Amount for 2i2c")

# %%
contracts_quarterly = contracts.resample("QE", on="Start Date").count()["index"].reset_index()
px.bar(contracts_quarterly.query("`Start Date` < '2024-07-01'"), x="Start Date", y="index", title="New contracts each quarter")
