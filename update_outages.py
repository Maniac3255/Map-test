import pandas as pd

sites = pd.read_csv("Sites-small.csv")

duke = sites[
    sites["Vendor Name"]
    .str.contains("Duke", na=False)
]

duke.to_csv(
    "duke_sites.csv",
    index=False
)

print(f"Found {len(duke)} Duke locations")
