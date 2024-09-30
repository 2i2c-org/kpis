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

# These correspond to AirTable URLs of the form:
#   airtable.com/{{ BASE ID }}/{{ TABLE ID }}/{{VIEW ID}}
views = [
    ("communities", "appbjBTRIbgRiElkr", "tblYGygEo5PQBSUYt", "viw2F6xVWJujWKCuj"),
    ("locations", "appbjBTRIbgRiElkr", "tblNiMH0gYRVhVdhE", "viwYjmYFRWWJnrv8Y"),
    ("accounting", "appbjBTRIbgRiElkr", "tblNjmVbPaVmC7wc3", "viw1daKSu2dTcd5lg"),
    ("contracts", "appbjBTRIbgRiElkr", "tbliwB70vYg3hlkb1", "viwWPJhcFbXUJZUO6"),
    ("leads", "appbjBTRIbgRiElkr", "tblmRU6U53i8o7z2I", "viw8xzzSXk8tPwBho"),
    ("sales", "appbjBTRIbgRiElkr", "tblBTPDI1nKoq8wOL", "viwcsrE83taP6GhSl"),
]
## Load in airtable
api = Api(api_key)
for (name, base_id, table_id, view_id) in views:
    print(f"Downloading {name} AirTable data from https://airtable.com/{base_id}/{table_id}/{view_id}...")
    table = api.table(base_id, table_id)
    records = table.all(view=view_id)
    # Add the AirTable ID for easy indexing later
    data = [r["fields"] | {"aid": r["id"]} for r in records]
    df = pd.DataFrame.from_records(data)
    
    # %% [markdown]
    # Write to a CSV file (not checked into git)
    
    # %%
    out_file = Path(here / f"../data/airtable-{name}.csv")
    df.to_csv(out_file, index=False)
print(f"Finished downloading latest AirTable community data to {out_file.resolve().parent}")
