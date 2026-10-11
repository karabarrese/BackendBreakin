"""
Central configuration + list of allowed machines
"""

import os

# Right now - I just am using my machine for the DB and not using a 
# website
TARGET_HOST = os.environ.get("LAB_TARGET_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("LAB_WEB_PORT", "8080"))      # the website front end
DB_PORT = int(os.environ.get("LAB_DB_PORT", "5432"))        # PostgreSQL

TARGET_ALLOWLIST = {"127.0.0.1", "localhost", "::1"}

# --- Gray-box starting knowledge --------------------------------------------
# The agent starts with what a low-privilege app user would have:
# it knows the DB is PostgreSQL and has a weak app-level account.
DB_NAME = os.environ.get("LAB_DB_NAME", "appdb")
DB_APP_USER = os.environ.get("LAB_DB_USER", "app_user")
DB_APP_PASSWORD = os.environ.get("LAB_DB_PASSWORD", "")  # blank = unknown

# --- Model ------------------------------------------------------------------
# Haiku is the cheapest
MODEL = os.environ.get("LAB_MODEL", "claude-haiku-4-5")

LOG_PATH = os.environ.get("LAB_LOG_PATH", "runs/latest.jsonl")


def assert_allowed(host: str) -> None:
    """Raise if `host` is not in the allowlist. Every tool calls this first."""
    if host not in TARGET_ALLOWLIST:
        raise PermissionError(
            f"Refusing to act against {host!r}: not in TARGET_ALLOWLIST "
            f"({sorted(TARGET_ALLOWLIST)}). This tool only runs against the local lab."
        )
