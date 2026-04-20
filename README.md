# Sector Rotation Screener

This repo contains a Streamlit-based sector and industry dashboard for visualizing market rotations and screening equities by sector and industry.

## Setup

1. Create and activate a Python virtual environment:

    python -m venv env
    source env/bin/activate    # Linux/Mac
    # env\Scripts\activate     # Windows


## Requirements

The app depends on:

- `pandas`
- `financedatabase==2.2.3`
- `yfinance`
- `tqdm`
- `streamlit`
- `altair`
- `scipy`
- `matplotlib`
- `pytest`
- `watchdog`

Install them with:

    pip install -r requirements.txt


3. Install `pytest` for tests if not already installed:

    pip install pytest

## Run the dashboard

From the `sector_rotation/` directory, start the Streamlit app:

    streamlit run dashboard.py

This loads the current package layout with source code under `sector_rotation/src/`.

## Run tests

From the same directory, execute:

    pytest


## Notes

- The project code is now located under `sector_rotation/src/`.
- The `sector_rotation/dashboard.py` file is a package wrapper that exposes the app entry point.
 