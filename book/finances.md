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

+++ {"editable": true, "slideshow": {"slide_type": ""}}

# Accounting and finance

This page summarizes 2i2c's financial picture, as well as our major cost and revenue trends.
Its goal is to provide transparency about how money is flowing through our organization.

(data-sources)=
```{admonition} Data sources
:class: dropdown

There are two data sources on this page, both of them are AirTable tables that are synced from CS&S data:

- **Accounting tables** are documented at {external:doc}`on our Accounting sources page <finance/accounting>`.
- **Invoicing data** are documented at {external:doc}`on our Invoices and Contracts page <finance/contracts>`.

**To update the AirTable data** see the instructions in [](scripts/clean_css_accounting_data.py).
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import pandas as pd
import plotly_express as px
from IPython.display import Markdown
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
df = pd.read_csv("data/airtable-accounting.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.drop(columns=["Category"]).rename(columns={"Category Major": "Category"})
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

Last updated **{sub-ref}`today`**.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
user_expressions:
- expression: f"{min_date:%Y-%m-%d}"
  result:
    data:
      text/plain: '''2023-07-01'''
    metadata: {}
    status: ok
- expression: f"{max_date:%Y-%m-%d}"
  result:
    data:
      text/plain: '''2024-03-31'''
    metadata: {}
    status: ok
---
min_date = df["Date"].min()
max_date = df["Date"].max()
Markdown(f"Showing data from **{min_date:%Y-%m-%d}** to **{max_date:%Y-%m-%d}**")
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
monthly = df.groupby("Category").resample("ME", on="Date").sum(["Cost", "Revenue", "Total"]).reset_index()

# This ensures we are at the start of each month so plotly doesn't round up
monthly["Date"] = monthly["Date"].dt.to_period("M").dt.to_timestamp()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
summary = []
for kind in ["Cost", "Revenue", "Total"]:
    subset = monthly.loc[:, ["Category", "Date", kind]]
    subset.loc[:, "Kind"] = kind
    subset = subset.rename(columns={kind: "Value"})
    summary.append(subset)
summary = pd.concat(summary)
summary = summary.groupby(["Date", "Kind"]).sum("Value").reset_index()
px.bar(summary, x="Date", y="Value", color="Kind",
       color_discrete_map={"Cost": "Red", "Revenue": "Green", "Total": "Grey"},
       barmode="group",
       title="Monthly revenue and costs, this FY"
)
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
for kind in ["Revenue", "Cost"]:
    fig = px.bar(monthly.query(f"{kind} > 0"), x="Date", y=kind, color="Category", title=f"Monthly {kind} by category, this FY", height=600, color_continuous_scale="Viridis")
    fig.show()
```

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input, full-width]
---
monthly_summary = monthly.groupby("Date").sum().reset_index()
monthly_summary["Revenue % of Costs"] = monthly_summary["Revenue"] / monthly_summary["Cost"]
mean_perc = monthly_summary["Revenue % of Costs"].mean()
fig = px.bar(monthly_summary, x="Date", y="Revenue % of Costs", title="Revenue as percentage of costs")
fig.add_hline(mean_perc, line_dash="dot")
fig.add_annotation(x=monthly_summary["Date"][6], y=mean_perc, ay=-50, text=f"Mean % of costs is {mean_perc:.0%}")
```
