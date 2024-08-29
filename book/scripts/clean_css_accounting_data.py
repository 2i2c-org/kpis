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
# This script does the following things:
#
# 1. Takes a CSV of the latest accounting transactions from CS&S.
# 2. Parses it into a single table of transactions.
# 3. Deletes all entries in [the Monthly Transactions AirTable](https://airtable.com/appbjBTRIbgRiElkr/pag7qUaeemormNSAf)
# 4. Uploads all of the new transactions to that table.
#
# ## Instructions
#
# To update the AirTable data, take the following steps:
#
# 1. Ensure you have an API token that can upload to AirTable in an environment variable called `AIRTABLE_API_KEY`
# 1. Find the latest accounting statement in [the CSS accounting folder](https://drive.google.com/drive/folders/1vM_QX1J8GW5z8W5WemxhhVjcCS2kEovN?usp=drive_link)
# 2. Download the {kbd}`Account Transactions` tab as a `.csv` file.
# 3. Place it in `data/css-accounting/`.
# 4. Run this script.
#
# ## For visualizations and summaries:
#
# :::{card} ⚡ Click for the monthly accounting interface
# :link: https://airtable.com/appbjBTRIbgRiElkr/pag7qUaeemormNSAf
# This summarizes our latest accounting data over time for review.
# :::
#

# ## Load data

import plotly_express as px
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
path = list(Path(here / "../data/css-accounting/").glob("*.csv"))[-1]
df = pd.read_csv(path, skiprows=6)

# Quick renaming
df = df.rename(columns={"Net (USD)": "Amount"})


# -

# ## Munge the dataframe

# +
# Parse the amount column
def parse_accounting_string(s):
    if not isinstance(s, str):
        # If not a string, just skip it
        return
    s = s.replace(',', '')  # Remove comma separators
    s = s.strip()  # Remove leading/trailing whitespace
    
    if s.startswith('(') and s.endswith(')'):
        # Handle parentheses for negative numbers
        return -float(s[1:-1])
    elif s.startswith('$'):
        # Handle dollar sign
        return float(s[1:])
    else:
        return float(s)
df["Amount"] = df["Amount"].map(parse_accounting_string)

# Remove category rows and add them as an entry
dfnew = []
active_category = None
for ix, irow in df.iterrows():
    if pd.isna(irow["Date"]) or irow["Date"].lower().startswith("Total"):
        # If empty, just skip it
        continue
    elif pd.isna(irow["Source"]):
        # If the source is empty, assume that it is a category and not a transaction
        active_category = irow["Date"]
    else:
        # Add the active category
        irow["Category"] = active_category
        irow["Kind"] = "revenue" if "revenue" in active_category.lower() else "cost"
        dfnew.append(irow)
dfnew = pd.DataFrame(dfnew)


# +
# Add major category for later use
def clean_category(cat):
    # Extract the category string
    # Each entry has a form like:
    #     NNNN - NNNN STRING
    cat = cat.split(" ", 3)[-1]

    # Return the major category
    if any(ii in cat for ii in ["Other", "Revenue"]):
        return cat.split(":")[-1]
    else:
        return cat.split(":")[0]
dfnew["Category Major"] = dfnew["Category"].map(clean_category)

# Date type
dfnew["Date"] = pd.to_datetime(dfnew["Date"])
print(f"Finished preparing {len(dfnew)} new items...")

# +
# If we want to inspect it
# ishow(dfnew)
# -

# ## Update AirTable

# Load the airtable records

# +
from pyairtable import Api
import pandas as pd
import os
from pathlib import Path

import sys
path_twoc = Path("../").resolve()
sys.path.append(str(path_twoc))
import twoc

# %%
## Load in airtable
api_key = twoc.api_key()
api = Api(api_key)
base_id = "appbjBTRIbgRiElkr"
table_id = "tblNjmVbPaVmC7wc3"
view_id = "viw1daKSu2dTcd5lg"
table = api.table(base_id, table_id)
records = table.all(view=view_id)
print(f"Found {len(records)} records...")
# -

# ### Delete
#
# Delete all current records

result = table.batch_delete([ii["id"] for ii in records])
print(f"Finished deleting {len(result)} results...")

# ### Create
#
# Create new records from the updated data.
#
# This will update [the plots at this interface](https://airtable.com/appbjBTRIbgRiElkr/pag7qUaeemormNSAf).

# +
# Convert to a records dict and remove empty columns
string_columns = ["Account Code", "Date", "Invoice Number", "Reference"]

# Stringify some columns
for col in string_columns:
    dfnew[col] = dfnew[col].map(str)

output = []
for ix, vals in dfnew.iterrows():
    # Remove any missing values
    vals = vals.dropna()
    
    # Stringify some columns
    for col in string_columns:
        if col not in vals:
            continue
        vals[col] = str(vals[col])

    # Make empty any string "none" values
    for key, val in vals.items():
        if any(val == ii for ii in ["None", "nan"]):
            vals[key] = ''
    output.append(vals.to_dict())
# -

results = table.batch_create(output, typecast=False)
print(f"Finished adding {len(results)} results...")

# ## Visualize

dfnew["Date"] = pd.to_datetime(dfnew["Date"])
for kind, idata in dfnew.groupby("Kind"):
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
