"""Simple in-process queue used for development and tests."""

import queue

# `queue.Queue` is threadsafe, making it adequate for the API thread and
# worker thread to communicate in our CI environment.
Q: "queue.Queue[str]" = queue.Queue()

