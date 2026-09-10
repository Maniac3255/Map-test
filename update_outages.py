import pandas as pd

sites = pd.read_csv("Sites-small.csv")

sce = sites[
    sites["Vendor Name"]
    .str.contains("Edi", case=False, na=False)
].copy()

active_outage = False

if active_outage:
    sce["Status"] = "OUTAGE"
    sce.to_csv("impacted_sites.csv", index=False)
else:
    pd.DataFrame(columns=list(sce.columns) + ["Status"]).to_csv(
        "impacted_sites.csv",
        index=False
    )

print("Finished outage check")
