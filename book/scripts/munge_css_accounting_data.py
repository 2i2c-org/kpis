# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# + [markdown] user_expressions=[]
# # Clean CS&S accounting data for use with our AirTable
#
# ## Instructions
#
# - Download latest data from our [Accounting Statements Folder](https://docs.google.com/spreadsheets/d/1PDpPAed_q35n1-xSNN1U9tzZg7tzzBVfpmGYFqMOneQ/edit?usp=share_link)
#   
#   > For example, here's [the account transactions up to 2023/01/31](https://docs.google.com/spreadsheets/d/1PDpPAed_q35n1-xSNN1U9tzZg7tzzBVfpmGYFqMOneQ/edit#gid=686580753)).
#   
# - Move to the `_data` folder here
# - Run this notebook
# - The final cell will copy the munged data to your clipboard
# - Paste this data to the [All Accounting Transactions](https://airtable.com/appbjBTRIbgRiElkr/tblDKGQFU0iEIa5Qb/viwAdsIgMwbqKDdZ0?blocks=hide) AirTable.
# - Make sure to **completely replace** the table with this updated data.
# -

import pandas as pd
from glob import glob

# +
# Read in the raw data which we'll need to clean a bit
datafiles = glob("_data/*.csv")

# First datafile will be the one with the latest date
raw = pd.read_csv(datafiles[0], header=6).dropna(subset=["Date"])

# +
# Create a copy so we can modify it
data = raw.copy()

# Remove "totals" rows
data = data.loc[~data["Date"].str.startswith("Total"), :]

# Define an account codes dictionary based on the category rows
category_rows = data.loc[data["Source"].isna(), :]
category_mapping = {}
for irow in category_rows["Date"].values:
    key, val = irow.split(" ", 1)
    category_mapping[int(key)] = val
    
# Remove the "summary" lines from our account codes
data = data.dropna(subset=["Source"])

# Update our data with these semantic account codes
data["Category"] = [category_mapping[int(ii)] for ii in data["Account Code"].values]

# Convert our `Net` column to a float instead of currency data
for ix, irow in data.iterrows():
    inet = irow["Net"]
    if inet.startswith("("):
        inet = f"-{inet}"
    for ichar in [",", "(", ")"]:
        inet = inet.replace(ichar, "")
    
    # Make inet a float to make sure it's possible
    inet = float(inet)

    # Add a type as revenue or cost
    # Receivable Invoices can show up in a "costs" section where we are billing directly for costs
    if "Receivable Invoice" in irow["Source"] or "Revenues" in irow["Category"]:
        data.loc[ix, "Revenue"] = inet
        data.loc[ix, "Cost"] = 0
    else:
        data.loc[ix, "Cost"] = inet
        data.loc[ix, "Revenue"] = 0
        
data = data.drop(columns=["Net"])

# + [markdown] user_expressions=[]
# ## Copy to clipboard to paste into AirTable
#
# You should be able to just copy/paste the dataset into [this AirTable now](https://airtable.com/appbjBTRIbgRiElkr/tblDKGQFU0iEIa5Qb/viwAdsIgMwbqKDdZ0).
# Make sure to delete the header row though.
# -

data.to_clipboard(index=False)

# + [markdown] user_expressions=[]
# ## If you want to preview the data
# -

data


