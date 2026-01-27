# 2i2c KPIs

This is a lightweight website to visualize some of 2i2c's Key Performance Indicators and major activity.
Its goal is to quickly let us look at the most important numbers to gauge the health and impact of our organization.[^1]

[^1]: These dashboards are generated with [Jupyter Book](https://jupyterbook.org) and the [MyST Markdown stack](https://myst.tools).
These are tools from the [ExecutableBooks project](https://executablebooks.org), one of 2i2c's key upstream communities.

````{grid}
```{grid-item-card} Cloud and hub usage ☁️
:link: cloud/
:link-type: doc

Our currently running infrastructure and active users over time.
```
```{grid-item-card} Accounting analysis 📈
:link: finances/
:link-type: doc
%
Our financial activity, including our costs and revenue broken down by category.
```
```{grid-item-card} Upstream support 💗
:link: upstream/
:link-type: doc

Our contributions and activity in key upstream communities that we depend on and use.
```
````

Below is a breakdown of the categories above with more information about their sub-sections.

```{toctree}
:maxdepth: 2

cloud
upstream
finances
marketing
people
```
