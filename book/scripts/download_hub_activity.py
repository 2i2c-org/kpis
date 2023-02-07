"""
Download activer user data from each of our JupyterHubs and save them to a CSV.
This uses the cluster and hub data in our config folder, and grabs the active users
data from the `metrics/` endpoint of each JupyterHub we run.

ref: https://github.com/2i2c-org/infrastructure/tree/master/config/clusters
"""
from rich import print
from rich.progress import Progress
import pandas as pd
from yaml import safe_load
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile
from pathlib import Path
from glob import glob

# TODO: In the future, we should download timeseries data from Prometheus so that
#       we can visualize this over time. This will be a bit more complex so for now we
#       just visualize the current data from each hub.
#
#       This comment has instructions for how to get the prometheus data:
#       ref: https://github.com/2i2c-org/infrastructure/issues/1785#issuecomment-1308494647

# Download the `infrastructure/` repository as a Zip file so we can inspect contents
# For now we don't use a token because this *should* only be a single operation.
URL_REPOSITORY_ZIP = "https://github.com/2i2c-org/infrastructure/archive/refs/heads/master.zip"
with urlopen(URL_REPOSITORY_ZIP) as zipresp:
    with ZipFile(BytesIO(zipresp.read())) as zfile:
        zfile.extractall('./_build/data/')

# These are the time scales that we know are in the hub's metrics
search_time_scales = {"24h": "Daily", "7d": "Weekly", "30d": "Monthly"}

clusters = glob("_build/data/infrastructure-master/config/clusters/*")
clusters = list(filter(lambda a: a != "templates", clusters))

df = []
with Progress() as progress:
    p_clusters = progress.add_task("Processing clusters...", total=len(clusters))
    p_hubs = None
    for cluster in clusters:
        # Load the configuration for this cluster
        cluster_yaml = Path(f"{cluster}/cluster.yaml")
        if not cluster_yaml.exists():
            print(f"Skipping folder {cluster} because no cluster.yaml file exists...")
            continue
        progress.update(p_clusters, description=f"Processing cluster {cluster.split('/')[-1]}...")
        config = cluster_yaml.read_text()
        config = safe_load(config)

        # Set up progress bar for the hubs on this cluster
        if p_hubs is None:
            p_hubs = progress.add_task("Processing hubs...", total=len(config["hubs"]))
        else:
            progress.update(p_hubs, total=len(config["hubs"]), completed=0)

        # Find the domain for this hub and grab its metrics
        for hub in config["hubs"]:
            hub_name = hub["domain"].replace(".2i2c.cloud", "")
            progress.update(p_hubs, description=f"Processing hub {hub_name}...")
            resp = urlopen(f'https://{hub["domain"]}/metrics').read()
            metrics = resp.decode().split("\n")
            # Search for jupyterhub_active_users lines and grab their values
            for iline in metrics:
                if "jupyterhub_active_users" not in iline:
                    continue
                    
                # We expect three time scales per hub
                for scale, name in search_time_scales.items():
                    if scale in iline:
                        users = int(float(iline.split()[-1]))
                        df.append({
                            "cluster": cluster.split("/")[-1],
                            "hub": hub["domain"],
                            "scale": name,
                            "users": users
                        })
            progress.update(p_hubs, advance=1)
        progress.update(p_clusters, advance=1)
      
# Convert to a to save as a CSV
df = pd.DataFrame(df)
path_out = Path(__file__).parent / ".." / "data" / "hub-activity.csv"
df.to_csv(path_out)
