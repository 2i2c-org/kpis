---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.2
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

```{code-cell} ipython3
%pip install gspread
```

```{code-cell} ipython3
import gspread

gc = gspread.service_account("data/google-service-account-key.json")
wks = gc.open_by_url(url)
worksheet = wks.worksheet("Summary")
```

```{code-cell} ipython3
df = worksheet.get_all_values()
```

```{code-cell} ipython3
pd.DataFrame(df)
```

```{code-cell} ipython3
from google.oauth2 import service_account
afrom googleapiclient.discovery import build

# Path to your JSON key file
key_path = './data/google-service-account-key.json'
```

```{code-cell} ipython3
from pathlib import Path
import gsheet_pandas

secret_path = Path('./data/').resolve()
gsheet_pandas.setup(credentials_dir=secret_path / 'google-service-account-key.json',
                    token_dir=secret_path / 'token.json')
```

```{code-cell} ipython3
import pandas as pd

spreadsheet_id = "1zDO_kqnJ1PH3GWOMks5E_1oIpoAJgseWhj3oCohUVZk"
sheet_name = "Expenses"
df = pd.from_gsheet(spreadsheet_id, 
                    sheet_name=sheet_name,
                    range_name='!A1:C100') # Range in Sheets; Optional
```

```{code-cell} ipython3
"""
This script automatically exports Google Sheets spreadsheets to local CSV files.
It is inspired by this blog post: https://skills.ai/blog/import-google-sheets-to-pandas/

Assumptions:
============
- There is a yaml file called `google_sheets.yaml` located next to the script
  with the following format:
```

  - url: <url of google sheet to download>
    filename: <filename to save the data as a csv to>
  ```
- The URLs of the Google Sheets must be publicly visible by anyone with the link
  in order to avoid needing to worry about authentication.
- We only care about downloading the first sheet of each Google Sheets file
  (This can be accommodated though if required)

Requirements:
=============
- pip install pandas pyyaml

Execution:
==========
- python download_google_sheets_to_csv.py
"""
import re
import yaml
import pandas as pd


def modify_google_sheet_url(url):
    """Modifies a Google Sheets URL for CSV export

    Args:
        url (str): The URL to modify
    """
    # Regular expression to match and capture the necessary part of the URL
    pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)(/edit#gid=(\d+)|/edit.*)?"

    # Remove 

    # Replace function to construct the new URL for CSV export
    #If gid is present in the URL, it includes it in the export URL, otherwise, it's omitted
    replacement = lambda m: f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?" + (f"gid={m.group(3)}&" if m.group(3) else "") + "format=csv"

    # Replace using regex
    new_url = re.sub(pattern, replacement, url)

    return new_url


# Make sure to remove any `?gid=` in there or the regex won't work
URL_base = "https://docs.google.com/spreadsheets/d/1zDO_kqnJ1PH3GWOMks5E_1oIpoAJgseWhj3oCohUVZk/edit#gid=637200569"
url = modify_google_sheet_url(URL_base)
df = pd.read_csv(url)
```

```{code-cell} ipython3
df = df.loc[~(df.isna().sum(1) == df.shape[1])]
```

```{code-cell} ipython3
df
```
