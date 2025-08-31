import os

# Disable optional middleware by default for tests
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOGGING_ENABLED", "false")

# Tests package
