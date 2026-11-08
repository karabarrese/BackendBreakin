"""
The agent's tools. Each tool is a plain Python function that returns a string.
Claude decides WHICH to call and with what arguments; these functions do the
actual work.

RECON:
  - recon_nmap : what services/ports are open on the lab host?
  - http_probe : fetch a URL from the lab website and show status + body
  - pg_query   : connect to PostgreSQL and run one query (gray-box app account)

TODO:
  #1 plaintext passwords   -> pg_query. No new tool.
  #2 secrets in the clear  -> pg_query. No new tool.
  #3 over-permissive grants-> a dedicated pg_privileges tool that lists a role's grants
  #4 weak/default creds    -> pg_query already takes user/password; a
                              try_credentials helper (test a list, report hits)
  #5 SQL injection (web)    -> http_probe, once lab_web.py exists. No new tool,
                              but needs the web server built (EXTENDING.md).
  #6 audit trail / tamper   -> pg_query (INSERT to write a trail, DELETE to
                              wipe it). No new tool; see the #6 notes.
"""

import shutil
import subprocess
import urllib.request
import config
import psycopg 


# Scan the lab host for open services. `ports` e.g. '5432,8080' or '1-10000'.
def recon_nmap(ports):
    if shutil.which("nmap") is None:
        return "ERROR: nmap is not installed. Install it (see SETUP.md) and retry."
    out = subprocess.run(
        ["nmap", "-sV", "-p", ports, config.DB_HOST],
        capture_output=True, text=True, timeout=120,
    )
    return out.stdout


# Send one HTTP request to the lab website and return status + headers + body.
def http_probe(path="/", method="GET", body=None):
    url = f"http://{config.WEB_HOST}:{config.WEB_PORT}{path}"
    data = body.encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as e:
        # urllib RAISES on 404/500/etc. For a probe, those are normal, useful
        # results -- return the status as text so the agent can keep going.
        page = e.read(8192).decode("utf-8", "replace")
        return f"HTTP {e.code} {url}\n{page}"
    text = resp.read(8192).decode("utf-8", "replace")
    headers = "".join(f"{k}: {v}\n" for k, v in resp.headers.items())
    return f"HTTP {resp.status} {url}\n{headers}\n{text}"

# Run one SQL statement against the lab database and return up to 50 rows.
# Defaults to the gray-box app account; pass user/password to try other creds.
def pg_query(sql, user=None, password=None):
    if psycopg is None:
        return "ERROR: psycopg is not installed. Run: pip install 'psycopg[binary]'"
    user = user or config.DB_APP_USER
    password = password if password is not None else config.DB_APP_PASSWORD
    try:
        with psycopg.connect(
            host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
            user=user, password=password, connect_timeout=10,
        ) as conn:
            cur = conn.cursor()
            cur.execute(sql)
            if cur.description is None:
                return f"OK (no rows). rowcount={cur.rowcount}"
            cols = [d.name for d in cur.description]
            rows = cur.fetchmany(50)
            lines = [" | ".join(cols)]
            for r in rows:
                lines.append(" | ".join(str(c) for c in r))
            return "\n".join(lines)
    except Exception as e:
        # Auth failure, bad SQL, permission denied, etc. -> return as TEXT
        # so the agent can read the result and keep going.
        return f"DB ERROR as user {user!r}: {type(e).__name__}: {e}"


COMMON_PASSWORDS = [
    "password", "password123", "123456", "admin", "admin123",
    "letmein", "root", "changeme", "anonymous",
    "mario", "welcome", "secret", "john", "monkey",
]

# Try a list of passwords for a DB user until one connects. -- challenge #4
def try_credentials(user, passwords=None):
    if psycopg is None:
        return "ERROR: psycopg is not installed. Run: pip install 'psycopg[binary]'"
    candidates = COMMON_PASSWORDS
    tried = 0
    for pw in candidates:
        tried += 1
        try:
            conn = psycopg.connect(
                host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
                user=user, password=pw, connect_timeout=10,
            )
            conn.close()
            return f"CRACKED: user '{user}' password is '{pw}' (after {tried} tries)"
        except psycopg.OperationalError as e:
            if "authentication" in str(e).lower() or "password" in str(e).lower():
                continue                      # wrong password -- keep going
            return f"ERROR (not an auth failure) after {tried} tries: {e}"
    return f"No common password matched for '{user}' ({tried} tried)."


# --- Tool schemas: how Claude learns what each tool does and what it takes ---
# Claude reads these descriptions to choose a tool, so keep them clear. When you
# add a tool, add its schema here AND a matching branch in agent.py (see
# EXTENDING.md).

TOOL_SCHEMAS = [
    {
        "name": "recon_nmap",
        "description": "Port/service scan of the lab host to see what is exposed "
                       "(e.g. is PostgreSQL 5432 reachable, is the website up).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ports": {"type": "string",
                          "description": "Ports to scan, e.g. '5432,8080' or a range '1-10000'."}
            },
        },
    },
    {
        "name": "http_probe",
        "description": "Send one HTTP request to the lab website and return the "
                       "status code, headers, and (truncated) body. Use this to "
                       "explore endpoints and test inputs through the front end.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "URL path, e.g. '/login' or '/search?q=x'."},
                "method": {"type": "string", "description": "HTTP method, default GET."},
                "body": {"type": "string", "description": "Optional request body (for POST)."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "pg_query",
        "description": "Run one SQL statement against the lab PostgreSQL database and "
                       "return up to 50 rows. Defaults to the gray-box app account. "
                       "Pass user/password to test other credentials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single SQL statement."},
                "user": {"type": "string", "description": "Optional DB username to try."},
                "password": {"type": "string", "description": "Optional DB password to try."},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "try_credentials",
        "description": "Try common passwords for a database user until one logs in. "
                   "Use this to demonstrate weak/default credentials. Pass a "
                   "'passwords' list to override the built-in common-password list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "description": "Database username to attack."},
                "passwords": {"type": "array", "items": {"type": "string"},
                              "description": "Optional custom password list to try."},
            },
            "required": ["user"],
        },
    },
]
