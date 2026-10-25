"""
Central configuration + the list of machines the agent is allowed to touch.

Every value here can be overridden with an environment variable, but the
defaults are set to work out-of-the-box against the lab that setup_lab.sql
creates. A fresh clone should run with nothing exported except your API key.
"""

import os

# --- Target -----------------------------------------------------------------
# The lab is loopback-only for direct DB access. 
# The Website will have an IP address or a http://sitename
DB_HOST = os.environ.get("LAB_TARGET_HOST", "127.0.0.1")
WEB_HOST = os.environ.get("LAB_TARGET_HOST", "127.0.0.1") # This will change when get get the website
WEB_PORT = int(os.environ.get("LAB_WEB_PORT", "8080"))    # I assume it will be port 80 or 8080
DB_PORT = int(os.environ.get("LAB_DB_PORT", "5432"))     # PostgreSQL

# --- Gray-box starting knowledge --------------------------------------------
# What a low-privilege app user would have on day one: it knows the DB is
# PostgreSQL and has a low-level account. 
# These are the defaults in setup_lab.sql (database "breach_lab", user "app_user" / "app_password").
DB_NAME = os.environ.get("LAB_DB_NAME", "breach_lab")
DB_APP_USER = os.environ.get("LAB_DB_USER", "app_user")
DB_APP_PASSWORD = os.environ.get("LAB_DB_PASSWORD", "app_password")

# --- Model ------------------------------------------------------------------
# Haiku is the cheapest. Override with LAB_MODEL to use a larger model.
MODEL = os.environ.get("LAB_MODEL", "claude-haiku-4-5")

LOG_PATH = os.environ.get("LAB_LOG_PATH", "runs/latest.jsonl")
