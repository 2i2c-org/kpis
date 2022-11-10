# Key Performance Indicators

A book to track our KPIs.

## To build the book locally

Use the `nox` tool like so:

```
nox -s build
```

This will install the necessary requirements and build the book locally.

## If there is an error

If there's an error in executing any of the cells above, you can browse the logs via the GitHub Action that is automatically run.

To do so:

- Go to the action page
- Click on the `Summary` tab, and then at the bottom download the `.zip`
- Scroll down to `Artifacts`
- Click the `zip` file for `sphinx-logs`
- The results of computation are in `sphinx-logs.zip\html\reports`
