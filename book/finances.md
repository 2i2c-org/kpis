---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.18.1
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

+++ {"editable": true, "slideshow": {"slide_type": ""}}

# Revenue projections

This document shows 2i2c's revenue projections by contract and predicts monthly income alongside costs using our HubSpot deals data. See [Understanding revenue](#understanding-revenue) below for details.

:::{admonition} To run this notebook locally
:class: dropdown
To see the visualizations locally, follow these steps:

1. Export a HubSpot private app token as `HUBSPOT_ACCESS_TOKEN` (or `HUBSPOT_TOKEN`).
2. Download the latest data (cached to `book/data/hubspot-deals.json`):

   ```bash
   python book/scripts/download_hubspot_data.py
   ```
3. Run this notebook from top to bottom.

Important fields in HubSpot:

- {kbd}`contract_start_date` / {kbd}`contract_end_date`: Dates for committed deals.
- {kbd}`target_start_date` / {kbd}`target_end_date`: Dates for pipeline deals that haven't closed yet.
- {kbd}`amount`: Total contract value (used to calculate MRR).
- {kbd}`hs_forecast_probability`: HubSpot's forecast probability for weighting pipeline revenue.
:::


```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import datetime
import os
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import twoc
from twoc.dates import round_to_nearest_month

twoc.set_plotly_defaults()

# This just suppresses a warning
pd.set_option("future.no_silent_downcasting", True)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRUl-GB46-plmuYxaZSK_IQxgzYI_MBGN8YffTdYS_267YqPrXvROgIQGT-Xspeug__Ut6nRPRDHGZ5/pub?gid=1482549235&single=true&output=csv"
costs = pd.read_csv(url, header=2).dropna()
costs = costs.rename(columns={"Summary": "Date"})
costs["Date"] = pd.to_datetime(costs["Date"])

# These costs *exclude* our fiscal sponsor fee.
# This is because all of the `opportunities` data subtracts the FSP fee in its amount
MONTHLY_COSTS = costs["Expenses"].head(5).mean()
ANNUAL_COSTS = MONTHLY_COSTS * 12
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
# Read cached HubSpot deals (refresh via scripts/download_hubspot_data.py)
data_path = Path("./data/hubspot-deals.json")
if not data_path.exists():
    raise FileNotFoundError(
        "Missing book/data/hubspot-deals.json. Run scripts/download_hubspot_data.py first."
    )

with data_path.open() as f:
    deals_raw = json.load(f)

deals = pd.json_normalize(deals_raw["results"])
deals.columns = deals.columns.str.replace("properties.", "")
deals = deals.rename(columns={"dealname": "Name"})

keep_cols = [
    "id",
    "Name",
    "amount",
    "dealstage",
    "contract_start_date",
    "contract_end_date",
    "target_start_date",
    "target_end_date",
    "closedate",
    "hs_forecast_probability",
]
deals = deals[[col for col in keep_cols if col in deals.columns]]
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
PROBABILITY_CUTOFF = 0.4
DEFAULT_PIPELINE_PROBABILITY = 0.5


def parse_probability(value):
    """Normalize HubSpot probability into [0, 1]."""
    if pd.isna(value):
        return np.nan
    prob = float(value)
    if prob > 1:
        prob = prob / 100
    return max(min(prob, 1.0), 0.0)


def classify_deal_size(amount, start, end, name):
    """Match deals-gantt buckets based on annualized revenue."""
    if isinstance(name, str):
        name_lower = name.lower()
        if ("czi" in name_lower) or ("navigation fund" in name_lower):
            return "OTHER"

    if pd.isna(amount):
        return "UNKNOWN"

    start = pd.to_datetime(start, errors="coerce")
    end = pd.to_datetime(end, errors="coerce")
    if pd.isna(start) or pd.isna(end):
        months = 12
    else:
        months = max(1, int(np.ceil((end - start).days / 30.44)))
    arr = (float(amount) / months) * 12
    if arr <= 10_000:
        return "SMALL"
    if arr < 45_000:
        return "MEDIUM"
    return "LARGE"


def get_pipeline_dates(row):
    """Pick start/end for pipeline deals with sensible fallbacks."""
    start = row.target_start_date
    end = row.target_end_date

    if (pd.isna(start) or pd.isna(end)) and pd.notna(row.closedate):
        start = row.closedate
        end = start + pd.DateOffset(years=1)

    return start, end


def generate_monthly_records(df):
    """Spread deal revenue across active months."""
    records = []
    for row in df.itertuples():
        amount = pd.to_numeric(row.amount, errors="coerce")
        stage = (row.dealstage or "").lower() if isinstance(row.dealstage, str) else ""

        if pd.isna(amount) or amount <= 0:
            continue
        if "closedlost" in stage:
            continue

        probability = 1.0
        deal_type = "Committed"
        start = pd.to_datetime(row.contract_start_date, errors="coerce")
        end = pd.to_datetime(row.contract_end_date, errors="coerce")

        if pd.isna(start) or pd.isna(end):
            deal_type = "Pipeline"
            start, end = get_pipeline_dates(row)
            probability = parse_probability(row.hs_forecast_probability)
            if pd.isna(probability):
                probability = DEFAULT_PIPELINE_PROBABILITY
            if probability < PROBABILITY_CUTOFF:
                continue

        # Convert to datetime first, then check before rounding
        start = pd.to_datetime(start, errors="coerce")
        end = pd.to_datetime(end, errors="coerce")
        if pd.isna(start) or pd.isna(end):
            continue

        start = round_to_nearest_month(start)
        end = round_to_nearest_month(end)

        months = pd.date_range(start, end, freq="MS")
        if len(months) == 0:
            months = pd.DatetimeIndex([start])
        n_months = max(len(months), 1)
        monthly_amount = float(amount) / n_months
        expected_monthly = monthly_amount * probability
        deal_size = classify_deal_size(amount, start, end, row.Name)

        for date in months:
            records.append(
                {
                    "Date": date,
                    "Total amount": float(amount),
                    "Monthly amount": monthly_amount,
                    "Monthly amount (expected)": expected_monthly,
                    "Probability": probability,
                    "Deal type": deal_type,
                    "Stage": row.dealstage,
                    "Name": row.Name,
                    "Deal size": deal_size,
                }
            )
    return pd.DataFrame(records)


date_cols = [
    "contract_start_date",
    "contract_end_date",
    "target_start_date",
    "target_end_date",
    "closedate",
]
for col in date_cols:
    deals[col] = pd.to_datetime(deals[col], errors="coerce")
deals["amount"] = pd.to_numeric(deals["amount"], errors="coerce")
deals["hs_forecast_probability"] = deals["hs_forecast_probability"].apply(
    parse_probability
)
deals["dealstage"] = deals["dealstage"].str.lower()
deals["Name"] = deals["Name"].fillna("Unnamed deal")

amortized_records = generate_monthly_records(deals)
amortized_records = amortized_records.query("Date >= '2022-01-01'")
amortized_records = amortized_records.sort_values("Monthly amount", ascending=False)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Historical query for the last 2 months through the next 18 months
today = datetime.datetime.today()
date_past = round_to_nearest_month(today - datetime.timedelta(days=30 * 3))
date_future = round_to_nearest_month(today + datetime.timedelta(days=30 * 18))

# Query for date range
qu_date = f"Date >= '{date_past:%Y-%m-%d}' and Date < '{date_future:%Y-%m-%d}'"
type_colors = {
    "Committed": "#0055cc",
    "Pipeline": "#f26c4f",
}

size_colors = {
    "SMALL": "#057761",   # forest
    "MEDIUM": "#1D4EF5",  # bigblue
    "LARGE": "#FF4E4F",   # coral
    "OTHER": "#B86BFC",   # mauve
    "UNKNOWN": "#A0A0A0",
}
size_domain = ["SMALL", "MEDIUM", "LARGE", "OTHER", "UNKNOWN"]

data_in_range = amortized_records.query(qu_date)
costs_in_range = costs.query(qu_date).sort_values("Date")

grouped_size = (
    data_in_range.groupby(["Date", "Deal size"], as_index=False).sum(numeric_only=True)
)
grouped_size["Name"] = grouped_size["Deal size"]

# Build Plotly figures for each chart
figures = {}
labels = ["committed", "weighted", "full", "by_size"]

for label in labels:
    data_plot = data_in_range.copy()

    if label == "committed":
        data_plot = data_plot.query("`Deal type` == 'Committed'")
        y_col = "Monthly amount"
        color_field = "Deal size"
        color_map = size_colors
        title = "Committed revenue (HubSpot contracts)"
    elif label == "weighted":
        y_col = "Monthly amount (expected)"
        color_field = "Deal type"
        color_map = type_colors
        title = "Monthly revenue (weighted by forecast probability)"
    elif label == "full":
        y_col = "Monthly amount"
        color_field = "Deal type"
        color_map = type_colors
        title = "Monthly revenue (full contract amount)"
    else:  # by_size
        data_plot = grouped_size
        y_col = "Monthly amount (expected)"
        color_field = "Deal size"
        color_map = size_colors
        title = "Monthly revenue by account size (weighted)"

    # Create bar chart
    fig = px.bar(
        data_plot,
        x="Date",
        y=y_col,
        color=color_field,
        title=title,
        color_discrete_map=color_map,
        hover_name="Name",
        hover_data={y_col: ":$,.0f"},
    )
    fig.update_traces(marker_line_width=0.2)

    # Add cost line
    fig.add_scatter(
        x=costs_in_range["Date"],
        y=costs_in_range["Expenses"],
        mode="lines",
        line_shape="hv",
        line_dash="dash",
        line_width=4,
        line_color="black",
        name="Costs",
    )

    figures[label] = fig
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Display figures directly
for fig in figures.values():
    fig.show()
```

(understanding-revenue)=
## Understanding revenue

The plots above show our revenue projections under different assumptions, going 18 months into the future:

1. Our **committed revenue** which only includes deals with contract dates in HubSpot.
2. Our **estimated revenue** where pipeline deals are weighted by HubSpot's forecast probability.
3. Our **best-case scenario revenue** which reflects revenue if every active/pipeline deal lands at full value.
4. Our **revenue by account size** showing the mix of deal sizes.

Note: All projections **exclude pipeline deals with < 40% forecast probability**.

### Deal classification

We pull deal data directly from HubSpot (via our deals-gantt dashboards) and split it into two buckets:

```{list-table}
- * **Committed deals**
  * Have contract dates and are treated as 100% reliable revenue.
- * **Pipeline deals**
  * Missing contract dates. We use target dates (or close date + 12 months as a fallback), HubSpot's forecast probability, and exclude `closedlost` stages.
```

Deals are also grouped by account size using the same buckets as deals-gantt:

```{list-table}
- * **SMALL**
  * ≤ $10k ARR
- * **MEDIUM**
  * $10k–$45k ARR
- * **LARGE**
  * ≥ $45k ARR
- * **OTHER**
  * Philanthropic / non-renewable (e.g., CZI, Navigation Fund)
```

### How we calculate revenue

````{admonition} How we weight and amortize revenue
:class: dropdown
- Committed deals use `amount / months_between(contract_start_date, contract_end_date)` for Monthly Recurring Revenue (MRR).
- Pipeline deals use the same calculation but are weighted by HubSpot's `hs_forecast_probability`.
- All values are spread evenly across active months for a deal.
````

## Understanding costs

Costs are manually calculated from [this Google Sheet](https://docs.google.com/spreadsheets/d/1OpKfPSIiFTY28OkV6--MhZygvdLVSdmpagjlnge2ELc/edit?usp=sharing) and **exclude our Fiscal Sponsor Fee** (because this fee is already subtracted from revenue projections above).

- **Assumed annual costs (no FSP)**: See plot above
- **Assumed monthly costs (no FSP)**: See plot above
