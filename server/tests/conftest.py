import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
SERVER_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(SERVER_ROOT, ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
