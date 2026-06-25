# Data Science Jobs Aggregator

This project collects Data Science openings with experience levels from 0 to 3 years, aggregates them from public sources, and refreshes them every day at 02:00 IST.

## Run locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the app:
   ```bash
   python app.py
   ```
3. Open http://localhost:5000

## Notes

The app currently pulls from public feeds and APIs when available and falls back to a small sample dataset if the remote providers are unavailable.
