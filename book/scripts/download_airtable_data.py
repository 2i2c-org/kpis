# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
from pyairtable import Api
import pandas as pd
import os
from pathlib import Path

# Define here based on whether we're interactive
if "__file__" in globals():
    here = Path(__file__).parent
else:
    here = Path(".")

# %%
# This API key is a secret in our KPIs repository as well
api_key = os.environ.get("AIRTABLE_API_KEY")
if not api_key:
    raise ValueError("Missing AIRTABLE_API_KEY")

base_id = 'appbjBTRIbgRiElkr'
table_id = 'tblYGygEo5PQBSUYt'
view_name = 'viw2F6xVWJujWKCuj'

## Load in airtable
api = Api(api_key)
table = api.table(base_id, table_id)
records = table.all(view=view_name)
df = pd.DataFrame.from_records((r['fields'] for r in records))

# %% [markdown]
# Write to a CSV file (not checked into git)

# %%
out_file = Path(here / "../data/airtable-communities.csv" )
df.to_csv(out_file, index=False)
print(f"Finished downloading latest AirTable community data to {out_file.resolve()}")
