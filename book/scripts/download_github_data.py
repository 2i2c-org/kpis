"""
Scrape GitHub activity in key stakeholder GitHub organizations for
all of 2i2c's team members. Store them in a local CSV file that is
used in visualization notebooks to plot activity over time.
"""
from github_activity import get_activity
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import os
from yaml import safe_load
from pathlib import Path
from copy import deepcopy

# Define here based on whether we're interactive
if "__file__" in globals():
    here = Path(__file__).parent
else:
    here = Path(".")

# Load data that we'll use for visualization
communities = safe_load((here / "../data/key-communities.yml").read_text())
team = safe_load((here / "../data/team.yml").read_text())

# If data already exists locally, load it
datetime_columns = ["createdAt", "updatedAt", "closedAt"]
path_data = Path(here / "../data/github-activity.csv")
if path_data.exists():
    data = pd.read_csv(path_data, parse_dates=datetime_columns)
else:
    data = None

# +
##
# Determine which dates we need to grab new data
##
# Use two quarters of data
N_DAYS = 182
# Use last year of data (for larger reports and grants)
# N_DAYS = 365 + 90
today = datetime.now(tz=ZoneInfo("UTC"))
time_window_begin = today - timedelta(days=N_DAYS)
time_window_end = today

# By default, we search 90 days in the past until the present
if data is not None:
    max_in_data = data["updatedAt"].max()
    if max_in_data > time_window_begin:
        time_window_begin = max_in_data  

# Uncomment this to manually define a start date
# start = datetime(2023, 1, 10, tzinfo=ZoneInfo("UTC"))
# -

# Break up our time window into windows of 60 days
# This helps us avoid hitting the 1000 node limit in GitHub API
time_breakpoints = []
time_window_checkpoint = deepcopy(time_window_begin)
while time_window_checkpoint < time_window_end:
    time_breakpoints.append(time_window_checkpoint)
    time_window_checkpoint += timedelta(days=60)
time_breakpoints.append(time_window_end)

# Download latest batch of data from GitHub
for community in communities:
    if time_window_end > today:
        print(f"time_window_end date {time_window_end} is less than {today}, no data to update...")
        continue

    # Download the data from GitHub using github_activity
    # We do this in windows of 2 months and then concat in one DataFrame
    data_new = []
    for ii in range(1, len(time_breakpoints)):
        start_time = time_breakpoints[ii-1]
        stop_time = time_breakpoints[ii]
        
        # Check for GitHub api authentication tokens and raise an error if none exist
        auth_keys = ["TOKEN_GITHUB_READONLY", "GITHUB_TOKEN"]
        for key in auth_keys:
            if key in os.environ:
                auth = os.environ.get(key)
                break
            auth = None
        if auth is None:
            print("No GitHub authentication token found, you will hit the rate limit...")
            print(f"Searched for these key names: {auth_keys}")

        print(f"Downloading activity in {community} from {start_time:%Y-%m-%d} to {stop_time:%Y-%m-%d}")
        data_new.append(get_activity(community, f"{start_time:%Y-%m-%d}", f"{stop_time:%Y-%m-%d}", auth=auth))
    data_new = pd.concat(data_new)
    
    # Clean up some fields so they're easier to work with later
    def _extract_node(item):
        """Extract any data that is nested in GraphQL sections."""
        if isinstance(item, dict):
            if "edges" in item:
                # It is a graphql list of edges
                nodes = [ii["node"] for ii in item["edges"]]
                return nodes
            if "login" in item:
                # It is a username
                return item["login"]
            if "oid" in item:
                # It is a merge commit
                return item["oid"]
        else:
            return item
    data_new = data_new.applymap(_extract_node)
    
    # Extract values from a few special-case columns
    data_new["mergedBy"]
    
    # Change datetime strings to objects
    for col in datetime_columns:
        data_new[col] = pd.to_datetime(data_new[col])
        
    # Save our final data or append it to pre-existing data
    if data is None:
        data = data_new
    else:
        # If there are duplicated rows (corresponding to unique IDs)
        # Keep the latest one (which is the newest data)
        data = pd.concat([data, data_new]).drop_duplicates("id", keep="last")


# +
# Remove data that is older than 3 months
data = data.loc[data["updatedAt"] > time_window_begin]

# Sort by id
data = data.sort_values("id")

# Save to CSV
data.to_csv(path_data, index=False)
print(f"Saved GitHub activity data to: {path_data.resolve()}")
