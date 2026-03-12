"""Validate the cloud data CSVs to make sure they have expected structure and aren't empty.
This is like a mini test-suite just to make sure data doesn't change unexpectedly in a big way.

Run after ./download.py!
"""

import sys
from pathlib import Path
import pandas as pd

here = Path(__file__).parent
DATA_DIR = here / "../../data"

# Map each CSV filename to the exact set of columns it should have.
# If Prometheus changes its output or the download script has a bug,
# we'll catch it here and raise an error so we can figure out what's going on.
EXPECTED = {
    "maus-by-hub.csv": {"date", "hub", "users", "cluster"},
    "maus-unique-by-cluster.csv": {"date", "cluster", "unique_users"},
}


def validate():
    errors = []
    for filename, expected_cols in EXPECTED.items():
        path = DATA_DIR / filename

        # Check the file was actually created by download.py
        if not path.exists():
            errors.append(f"{filename} does not exist, run download.py first")
            continue

        df = pd.read_csv(path)

        # An empty file means Prometheus returned nothing — likely an auth or connectivity issue
        if len(df) == 0:
            errors.append(f"{filename} is empty")

        # Column mismatch means the Prometheus query output changed shape,
        # or the download script's parsing broke
        if set(df.columns) != expected_cols:
            errors.append(
                f"{filename} has unexpected columns: {list(df.columns)} "
                f"(expected {sorted(expected_cols)})"
            )

    # Sanity check: verify a known historical data point hasn't changed.
    # If this fails, the Prometheus query or data pipeline has silently changed.
    # Reference: September 2025 unique users for utoronto cluster.
    # When the data window moves past this date, update REFERENCE_DATE,
    # REFERENCE_CLUSTER, and REFERENCE_VALUE to a recent known-good month-end.
    REFERENCE_DATE = "2025-09-30"
    REFERENCE_CLUSTER = "utoronto"
    REFERENCE_VALUE = 5689

    unique_path = DATA_DIR / "maus-unique-by-cluster.csv"
    if unique_path.exists():
        df_unique = pd.read_csv(unique_path)
        ref = df_unique.query(
            "date == @REFERENCE_DATE and cluster == @REFERENCE_CLUSTER"
        )
        if len(ref) == 1:
            actual = int(ref.iloc[0]["unique_users"])
            if actual != REFERENCE_VALUE:
                errors.append(
                    f"Historical data changed: {REFERENCE_CLUSTER} {REFERENCE_DATE} "
                    f"unique_users expected {REFERENCE_VALUE}, got {actual}"
                )
        elif len(ref) == 0:
            errors.append(
                f"Reference date {REFERENCE_DATE} is no longer in the data. "
                f"Update REFERENCE_DATE/VALUE in validate.py to a recent month-end."
            )

    return errors


if __name__ == "__main__":
    print("Validating cloud data...")
    errors = validate()
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    print("Validation passed.")
