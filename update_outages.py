import pandas as pd

sites = pd.read_csv("Sites-small.csv")

sce = sites[
    sites["Vendor Name"]
    .str.contains("Southern California Edision", na=False)
].copy()

sce["Status"] = "NORMAL"

sce.to_csv(
    "sce_sites.csv",
    index=False
)

print(f"Found {len(sce)} SCE locations")
