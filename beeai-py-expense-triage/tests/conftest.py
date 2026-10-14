import os

# The app has no @opik.track decorators (tracing is OpenTelemetry), but the Opik SDK honours this
# flag too; setting it keeps the suite offline whatever gets imported.
os.environ.setdefault("OPIK_TRACK_DISABLE", "true")
