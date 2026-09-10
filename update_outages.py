import pandas as pd

data = pd.DataFrame([
    ["12345", "OUTAGE"]
])

data.columns = [
    "Site #",
    "Status"
]

data.to_csv(
    "impacted_sites.csv",
    index=False
)

print("Updated outages file")
