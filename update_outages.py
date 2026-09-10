import pandas as pd

sites = pd.read_csv("Sites-small.csv")

sce = sites[
    sites["Vendor Name"]
    .str.contains("Edision", case=False, na=False)
]

sce.to_csv(
    "sce_sites.csv",
    index=False
)

print(f"Found {len(sce)} SCE locations")

