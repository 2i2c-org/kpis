"""Download hub activity and unique users data from Grafana/Prometheus.

Produces two CSV files in book/data/:
- maus-by-hub.csv: monthly active users per hub, sampled each day (this just uses the MAU metric from JupyterHub)
- maus-unique-by-cluster.csv: unique users per cluster, deduplicated across hubs, sampled roughly each *week*. This uses a custom prometheus query.

Requires GRAFANA_TOKEN environment variable.
"""

import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from prometheus_pandas.query import Prometheus
import pandas as pd
from rich.progress import track

load_dotenv(override=False)
GRAFANA_TOKEN = os.environ["GRAFANA_TOKEN"]
GRAFANA_URL = "https://grafana.pilot.2i2c.cloud"

here = Path(__file__).parent
DATA_DIR = here / "../../data"


def get_prometheus_datasources():
    """List the Prometheus datasources available in Grafana."""
    datasources = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GRAFANA_TOKEN}",
        },
    )
    df = pd.DataFrame.from_dict(datasources.json())
    return df.query("type == 'prometheus'")


def get_pandas_prometheus(prometheus_uid: str):
    """Create a Prometheus client for a given datasource uid."""
    session = requests.Session()
    session.headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    proxy_url = f"{GRAFANA_URL}/api/datasources/proxy/uid/{prometheus_uid}/"
    return Prometheus(proxy_url, session)


def download_hub_activity(datasources):
    """Download monthly active users per hub across all clusters."""
    query = """
        max(jupyterhub_active_users{period="30d", namespace=~".*"}) by (namespace)
    """

    path = DATA_DIR / "maus-by-hub.csv"
    print(f"Downloading hub activity data to {path}...")

    activity = []
    errors = []
    for uid, idata in track(list(datasources.groupby("uid"))):
        cluster_name = idata["name"].squeeze()
        try:
            prometheus = get_pandas_prometheus(uid)
            result = prometheus.query_range(
                query,
                datetime.today() - timedelta(days=365),
                datetime.today(),
                "1d",
            )
            # Extract hub name from column labels like '{namespace="hubname"}'
            result.columns = [re.findall(r'[^"]+', col)[1] for col in result.columns]
            result.columns.name = "hub"
            result.index.name = "date"
            result.index = result.index.floor("D")

            # Reshape to tidy format
            result = result.stack("hub").to_frame("users").reset_index()
            result["cluster"] = cluster_name
            activity.append(result)
        except Exception:
            errors.append(cluster_name)

    activity = pd.concat(activity)
    activity.to_csv(path, index=False)
    print(f"Finished: {path}")
    if errors:
        print(f"Clusters with errors: {', '.join(sorted(set(errors)))}")
    return path


def download_unique_users(datasources):
    """Download unique users per cluster (deduplicated across hubs).

    Sampled weekly + at month-ends for smooth curves and clean monthly totals.
    """
    # This query counts unique usernames across all hubs on a cluster.
    # It finds all jupyter user pods in the last 30 days and counts the distinct usernames
    query = """
        count(
          count by (annotation_hub_jupyter_org_username) (
            max_over_time(
              kube_pod_annotations{
                namespace=~".*",
                pod=~"jupyter-.*",
                annotation_hub_jupyter_org_username=~".+"
              }[30d]
            )
          )
        )
    """

    path = DATA_DIR / "maus-unique-by-cluster.csv"
    print(f"Downloading unique users per cluster to {path}...")

    # Build query dates: weekly + month-ends over the last 12 months
    today = datetime.today()
    start = today - timedelta(days=365)
    # This makes sure we have regular sampling to product smoother plots
    weekly_dates = pd.date_range(start=start, end=today, freq="7D")
    # This makes sure we have a month-end for our monthly MAU calculations
    month_end_dates = pd.date_range(start=start, end=today, freq="ME")
    query_dates = sorted(
        set(weekly_dates.to_pydatetime()) | set(month_end_dates.to_pydatetime())
    )

    # This loops through all the sources that Grafana listed (e.g. clusters) and grabs unique users based on username
    unique_users = []
    errors = []
    for uid, idata in track(list(datasources.groupby("uid"))):
        cluster_name = idata["name"].squeeze()
        try:
            prometheus = get_pandas_prometheus(uid)
            for qdate in query_dates:
                result = prometheus.query(query, qdate)
                if result.empty:
                    continue
                unique_users.append(
                    {
                        "date": qdate.strftime("%Y-%m-%d"),
                        "cluster": cluster_name,
                        "unique_users": int(result.iloc[0]),
                    }
                )
        # Sometimes clusters seem to error in ways that aren't totally clear, so this just tracks the ones that did
        except Exception:
            errors.append(cluster_name)

    if unique_users:
        pd.DataFrame(unique_users).to_csv(path, index=False)
        print(f"Finished: {path}")
    else:
        print("WARNING: No unique users data could be downloaded.")

    if errors:
        print(f"Clusters with errors: {', '.join(sorted(set(errors)))}")
    return path


if __name__ == "__main__":
    datasources = get_prometheus_datasources()
    download_hub_activity(datasources)
    download_unique_users(datasources)
