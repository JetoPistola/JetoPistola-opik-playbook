import os

# Set before anything imports opik: tests never talk to Opik, and no provider key is needed.
os.environ.setdefault("OPIK_TRACK_DISABLE", "true")
