name: Update Outage Map

on:
  schedule:
    - cron: "*/10 * * * *"   # Run every 10 minutes
  workflow_dispatch:         # Allow manual runs

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0     # IMPORTANT: allows pulling latest changes

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          pip install pandas requests pyproj

      - name: Run outage script
        run: python outage.py

      - name: Configure Git
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"

      - name: Pull latest changes (fixes push rejection)
        run: git pull origin main --rebase

      - name: Commit changes
        run: |
          git add outages.json impacted_sites.csv
          git commit -m "Auto-update outage map" || echo "No changes to commit"

      - name: Push changes
        run: git push origin main
