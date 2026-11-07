import os
import sys

# Flat imports: the repo root (for the game code), then this folder (for
# the test helpers).
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from hypothesis import HealthCheck, settings  # noqa: E402

settings.register_profile(
    "engine",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
settings.load_profile("engine")
