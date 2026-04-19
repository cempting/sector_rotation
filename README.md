---
# this repo enterains a tool to visualize the current stock trends
# aims to help with spotting market rotations but also screening for breakouts
# it presents the sectors, from there you can navigate to the industries of each sector
# and finally go into the respective stocks

---

# Setup
Create a Python env and install all required dependencies

    python -m venv env
    source env/bin/activate    # Linux/Mac
    # env\Scripts\activate     # Windows

    pip install -r requirements.txt

# Execute

    # Combined sector and industry dashboard
    python dashboard_sector_rotation.py
    streamlit run dashboard.py

    # Industry listing with ETF suggestions
    python industry_rotation.py "XLK"  # or sector name 