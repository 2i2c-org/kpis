# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# Clean the "All accounting transactions" tab of a monthly CS&S accounting statement and return it in a tabular form that we can upload easily into AirTable.
#
# To update the AirTable data, take the following steps:
#
# 1. Download the {kbd}`Account Transactions` tab as a `.csv` file.
# 2. Place it in `data/css-accounting.csv`.
# 3. Run this script.
# 4. Find the cleaned data at `data/css-accounting-cleaned.csv`
# 5. Delete all the records in [the AirTable {kbd}`Monthly Statement Transactions` tab](https://airtable.com/appbjBTRIbgRiElkr/tblNjmVbPaVmC7wc3/viw1daKSu2dTcd5lg?blocks=hide)
# 6. On {kbd}`Monthly Statement Transactions`, right-click, then {kbd}`Import data` -> {kbd}`CSV file`
# 7. Upload the new CSV file, click {kbd}`Exclude first row`
#
# This AirTable dataset will now be accessible to our accounting page builds.

# +
import pandas as pd
from pathlib import Path
from os import environ

# Define here based on whether we're interactive
if "__file__" in globals():
    here = Path(__file__).parent
else:
    here = Path(".")

path = Path(here / "../data/css-accounting.csv")
df = pd.read_csv(path, skiprows=6)
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
        # Make the number string more sensible
        for icat in ["Debit", "Credit"]:
            irow[icat] = float(irow[icat].replace(",", ""))
        dfnew.append(irow)
dfnew = pd.DataFrame(dfnew)

# Recalculate total so that it is negative where it needs to be
dfnew["Total"] = dfnew["Credit"] - dfnew["Debit"]
dfnew = dfnew.drop(columns=["Gross"])

# Rename columns
dfnew = dfnew.rename(columns={"Credit": "Revenue", "Debit": "Cost"})

# Add major category for later use
def clean_category(cat):
    if any(ii in cat for ii in ["Other", "Revenue"]):
        return cat.split(":")[-1]
    else:
        return cat.split(":")[0].split(maxsplit=1)[-1]
dfnew["Category Major"] = dfnew["Category"].map(clean_category)

# Create a new CSV that we'll use
newpath = path.parent / (path.stem + "-cleaned" + path.suffix)
dfnew.to_csv(newpath, index=False)
