import os
import sys

# Ensure the workspace root is on sys.path so the sector_rotation package can be imported
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
