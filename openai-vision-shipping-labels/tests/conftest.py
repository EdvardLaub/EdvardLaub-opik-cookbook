import os

# Offline tests: no Opik uploads and no real provider key needed.
os.environ.setdefault("OPIK_TRACK_DISABLE", "true")
os.environ.setdefault("OPENAI_API_KEY", "not-a-real-key")
