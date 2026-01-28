---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.17.2
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

+++ {"editable": true, "slideshow": {"slide_type": ""}}

# Marketing

This is a dashboard for quick reference for marketing measures.
It's not strictly a KPI dashboard, more of a place to keep useful information.

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-cell]
---
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import plotly.express as px
import pandas as pd
import twoc

twoc.set_plotly_defaults()

# Fetch and parse RSS feed
response = requests.get("https://2i2c.org/blog/index.xml")
root = ET.fromstring(response.content)

# Extract post data
posts = []
for item in root.findall('.//item'):
    pub_date = item.find('pubDate')
    if pub_date is not None:
        try:
            date_str = pub_date.text.rsplit(' ', 1)[0]  # Remove timezone
            post_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S')
            
            posts.append({
                'date': post_date,
                'title': item.find('title').text if item.find('title') is not None else 'Untitled',
                'url': item.find('link').text if item.find('link') is not None else ''
            })
        except (ValueError, AttributeError):
            continue

# Create DataFrame and filter to last 12 months
df = pd.DataFrame(posts)
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date'])  # Remove rows with invalid dates
cutoff = pd.Timestamp.now() - pd.DateOffset(months=12)
recent_df = df[df['date'] >= cutoff]
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Average number of blog posts per month

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Calculate monthly stats
monthly = recent_df.set_index('date').resample('ME').size()
stats = pd.DataFrame({
    'month': monthly.index.strftime('%B %Y'),
    'total_posts': monthly.values,
    'weekly_average': monthly.values / 4.33
})

# Calculate percentage change from previous month
stats['total_posts_pct_change'] = stats['total_posts'].pct_change() * 100
stats['weekly_avg_pct_change'] = stats['weekly_average'].pct_change() * 100

# Plot average weekly posts
fig1 = px.bar(stats, x='month', y='weekly_average',
              title='Average Weekly Blog Posts by Month (Last 12 Months)',
              custom_data=['weekly_avg_pct_change'])
fig1.update_traces(hovertemplate='<b>%{x}</b><br>Weekly Average: %{y:.2f}<br>Change from prev month: %{customdata[0]:.1f}%<extra></extra>')
fig1.update_layout(xaxis_tickangle=-45, height=500)
fig1.show()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## Total blog posts per month

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
# Plot total posts per month
fig2 = px.bar(stats, x='month', y='total_posts',
              title='Total Blog Posts by Month (Last 12 Months)',
              custom_data=['total_posts_pct_change'])
fig2.update_traces(hovertemplate='<b>%{x}</b><br>Total Posts: %{y}<br>Change from prev month: %{customdata[0]:.1f}%<extra></extra>')
fig2.update_layout(xaxis_tickangle=-45, height=500)
fig2.show()
```

+++ {"editable": true, "slideshow": {"slide_type": ""}}

## List of blog posts

```{code-cell} ipython3
---
editable: true
slideshow:
  slide_type: ''
tags: [remove-input]
---
from IPython.display import Markdown

# Create bulleted list with hyperlinked titles
bullet_list = []
for _, row in recent_df.iloc[:10].iterrows():
    date_str = row['date'].strftime('%Y-%m-%d')
    title = row['title']
    url = row['url']
    bullet_list.append(f"* {date_str} - [{title}]({url})")

markdown_output = "\n".join(bullet_list)
Markdown(markdown_output)
```
