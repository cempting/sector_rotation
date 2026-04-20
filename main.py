import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

from src.dashboard import main


if __name__ == "__main__":
    main()
