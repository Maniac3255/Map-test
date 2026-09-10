import pandas as pd

sites = pd.read_csv("Sites-small.csv")

sites["Status"] = "NORMAL"

# Test outage
sites.loc[0:4, "Status"] = "OUTAGE"

outages = sites[sites["Status"] == "OUTAGE"]

outages.to_csv(
    "impacted_sites.csv",
    index=False
)

print(f"Created {len(outages)} outage records")
