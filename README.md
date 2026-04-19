---
# this repo enterains a to visualize sector etfs 
---

# Setup
Create a Python env and install all required dependencies

    python -m venv env
    source env/bin/activate    # Linux/Mac
    # env\Scripts\activate     # Windows

    pip install -r requirements.txt

# Execute

    # Sector dashboard
    python dashboard_sector_rotation.py
    streamlit run dashboard_sector_rotation.py

    # Industry listing with ETF suggestions
    python industry_rotation.py "XLK"  # or sector name

    # Industry dashboard with ETF charts
    streamlit run industry_dashboard.py 