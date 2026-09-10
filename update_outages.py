import pandas as pd

sites = pd.read_csv("Sites-small.csv")

sce = sites[
    sites["Vendor Name"]
    .str.contains("Edi", case=False, na=False)
].copy()

sce["Status"] = "OUTAGE"

sce.to_csv(
    "impacted_sites.csv",
    index=False
)

print(f"Created {len(sce)} outage records")
