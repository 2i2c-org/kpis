# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Clean monthly accounting transactions for upload to AirTable
#
# Clean the "All accounting transactions" tab of a monthly CS&S accounting statement and return it in a tabular form that we can upload easily into AirTable.
#
# ## Instructions
#
# To update the AirTable data, take the following steps:
#
# 1. Find the latest accounting statement in [the CSS accounting folder](https://drive.google.com/drive/folders/1vM_QX1J8GW5z8W5WemxhhVjcCS2kEovN?usp=drive_link)
# 2. Download the {kbd}`Account Transactions` tab as a `.csv` file.
# 4. Place it in `data/css-accounting/`.
# 5. Run this script.
# 6. Find the cleaned data at `data/css-accounting/*-cleaned.csv`
# 7. Delete all the records in [the AirTable {kbd}`Monthly Statement Transactions` tab](https://airtable.com/appbjBTRIbgRiElkr/tblNjmVbPaVmC7wc3/viw1daKSu2dTcd5lg?blocks=hide)
# 8. On {kbd}`Monthly Statement Transactions`, right-click, then {kbd}`Import data` -> {kbd}`CSV file`
# 9. Upload the new CSV file, click {kbd}`Exclude first row`
#
# ## For visualizations and summaries:
#
# :::{card} ⚡ Click for the monthly accounting interface
# :link: https://airtable.com/appbjBTRIbgRiElkr/pag7qUaeemormNSAf
# This summarizes our latest accounting data over time for review.
# :::
#

# ## Load data

import plotly.express as px
import pandas as pd
from pathlib import Path
from os import environ
from itables import show as ishow

# +
# Define here based on whether we're interactive
if "__file__" in globals():
    here = Path(__file__).parent
else:
    here = Path(".")

# Take the first CSV file in the accounting folder
path = list(Path(here / "../data/css-accounting/").glob("*.xlsx"))[-1]
df = pd.read_excel(path, skiprows=6)

# Quick renaming
df = df.rename(columns={"Net (USD)": "Amount", "Account": "Category", "Account Type": "Category Type"})

# Drop empty rows
df = df.dropna(subset=["Description"])


# -

# ## Munge the dataframe

# +
# Add major category for later use
def clean_category(cat):
    # Extract the category string
    # Each entry has a form like:
    #     NNNN STRING
    cat = cat.split(" ", 1)[-1]

    # Return the major category
    if any(ii in cat.lower() for ii in ["other", "revenue"]):
        return cat.split(":")[-1]
    else:
        return cat.split(":")[0]
df["Category Major"] = df["Category"].map(clean_category)

# Date type
df["Date"] = pd.to_datetime(df["Date"])
# -

# ## Save to CSV for upload
#

# Create a new CSV that we'll use
newpath = path.parent / (path.stem + "-cleaned.csv")
df.to_csv(newpath, index=False)

# ## Visualize

for kind, idata in df.groupby("Category Type"):
    monthly = idata.groupby("Category Major").resample("ME", on="Date").sum()["Amount"].reset_index()
    totals = monthly.groupby("Date").sum("Amount")
    fig = px.line(monthly, x="Date", y="Amount", color="Category Major", height=600, title=f"Monthly {kind}")
    fig.add_scatter(
        x=totals.index,
        y=totals["Amount"],
        mode="lines",
        line_width=4,
        line_color="black",
        name="Total",
    )
    fig.show()


