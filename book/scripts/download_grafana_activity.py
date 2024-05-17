# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# Download the last 6 months of hub activity from Grafana, and store it for later use.
#
# Heavily inspired by Jenny's Grafana download guide:
#
# ref: https://compass.2i2c.org/partnerships/community_success/hub-activity/

# + editable=true slideshow={"slide_type": ""}
import os
import re
import requests
from pathlib import Path
from textwrap import dedent
from dotenv import load_dotenv
from dateparser import parse as dateparser_parse
from prometheus_pandas.query import Prometheus
import pandas as pd
from rich.progress import track

# -

load_dotenv(override=False)
GRAFANA_TOKEN = os.environ["GRAFANA_TOKEN"]


def get_prometheus_datasources(grafana_url: str, grafana_token: str) -> pd.DataFrame:
    """
    List the datasources available in a Grafana instance.

    Parameters
    ----------
    grafana_url: str
        API URL of Grafana for querying. Must end in a trailing slash.

    grafana_token: str
        Service account token with appropriate rights to make this API call.
    """
    api_url = f"{grafana_url}/api/datasources"
    datasources = requests.get(
        api_url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {grafana_token}",
        },
    )
    # Convert to a DF so that we can manipulate more easily
    df = pd.DataFrame.from_dict(datasources.json())
    # Move "name" to the first column by setting and resetting it as the index
    df = df.set_index("name").reset_index()
    return df


def get_pandas_prometheus(grafana_url: str, grafana_token: str, prometheus_uid: str):
    """
    Create a Prometheus client and format the result as a pandas data stucture.

    Parameters
    ----------
    grafana_url: str
        URL of Grafana for querying. Must end in a trailing slash.

    grafana_token: str
        Service account token with appropriate rights to make this API call.

    prometheus_uid: str
        uid of Prometheus datasource within grafana to query.
    """

    session = requests.Session()  # Session to use for requests
    session.headers = {"Authorization": f"Bearer {grafana_token}"}

    proxy_url = f"{grafana_url}/api/datasources/proxy/uid/{prometheus_uid}/"  # API URL to query server
    return Prometheus(proxy_url, session)


# +
# Fetch all available data sources for our Grafana
datasources = get_prometheus_datasources(
    "https://grafana.pilot.2i2c.cloud", GRAFANA_TOKEN
)

# Filter out only the datasources associated with Prometheus.
# These are the ones associated with cluster hub activity
datasources = datasources.query("type == 'prometheus'")
# -

# Download daily and monthly active users in 1 day increments over the last 6 months.
#
# Save this to a CSV file and load from this file instead of downloading if it exists.

# +
queries = {
    "daily": dedent(
        """
                    max(
                      jupyterhub_active_users{period="24h", namespace=~".*"}
                    ) by (namespace)
            """
    ),
    "monthly": dedent(
        """
                    max(
                      jupyterhub_active_users{period="30d", namespace=~".*"}
                    ) by (namespace)
            """
    ),
}

# Define here based on whether we're interactive
if "__file__" in globals():
    here = Path(__file__).parent
else:
    here = Path(".")

path_activity = Path(here / "../data/hub-activity.csv")
if not path_activity.exists():
    print(f"No hub activity data found at {path_activity}, downloading...")
    activity = []
    errors = []
    for queryname, query in queries.items():
        for uid, idata in track(list(datasources.groupby("uid"))):
            try:
                # Set up prometheus for this cluster and grab the activity
                prometheus = get_pandas_prometheus(
                    "https://grafana.pilot.2i2c.cloud", GRAFANA_TOKEN, uid
                )
                iactivity = prometheus.query_range(
                    query,
                    dateparser_parse("12 months ago"),
                    dateparser_parse("now"),
                    "1d",
                )
                # Extract hub name from the brackets
                iactivity.columns = [
                    re.findall(r'[^"]+', col)[1] for col in iactivity.columns
                ]
                iactivity.columns.name = "hub"

                # Clean up the timestamp into a date
                iactivity.index.name = "date"
                iactivity.index = iactivity.index.floor("D")

                # Re-work so that we're tidy
                iactivity = iactivity.stack("hub").to_frame("users")
                iactivity = iactivity.reset_index()

                # Add metadata so that we can track this later
                iactivity["cluster"] = idata["name"].squeeze()
                iactivity["timescale"] = queryname

                # Add to our list so that we concatenate across all clusters
                activity.append(iactivity)
            except Exception:
                errors.append((uid, idata["name"].squeeze()))

    # Convert into a DF and do a little munging
    activity = pd.concat(activity)

    # Write to a CSV for future ref
    activity.to_csv(path_activity, index=False)
    print(f"Finished loading hub activity data to {path_activity}...")
    if errors:
        serrors = "\n".join(f"- {error}" for error in errors)
        print(f"The following clusters had errors: {serrors}")
else:
    print(f"Found data at {path_activity}, not downloading...")
