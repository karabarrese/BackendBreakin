"""
The agent's tools. Each tool is just a normal Python function that returns a
string. Claude decides WHICH to call and with what arguments;

For the first step recon tools:
  - recon_nmap : what services/ports are exposed on the lab host?
  - http_probe : fetch a URL from the lab website and show status + body
  - pg_query   : connect to PostgreSQL and run a query (gray-box app account)

TBD - add exploitation tools
"""

import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Optional

import config

try:
    import psycopg  # psycopg 3 ("pip install psycopg[binary]")
except ImportError:  # keep the import soft so recon still works without it
    psycopg = None


def recon_nmap(ports: str = "1-10000") -> str:
    """Scan the lab host for open services. `ports` e.g. '5432,8080' or '1-10000'."""
    config.assert_allowed(config.TARGET_HOST)
    if shutil.which("nmap") is None:
        return "ERROR: nmap is not installed. Install it (see README) and retry."
    try:
        out = subprocess.run(
            ["nmap", "-sV", "-p", ports, config.TARGET_HOST],
            capture_output=True, text=True, timeout=120,
        )
        return (out.stdout or "") + (("\n[stderr]\n" + out.stderr) if out.stderr else "")
    except subprocess.TimeoutExpired:
        return "ERROR: nmap timed out after 120s."


def http_probe(path: str = "/", method: str = "GET", body: Optional[str] = None) -> str:
    """Send one HTTP request to the lab website and return status + headers + body (truncated)."""
    config.assert_allowed(config.TARGET_HOST)
    url = f"http://{config.TARGET_HOST}:{config.WEB_PORT}{path}"
    data = body.encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read(8192).decode("utf-8", "replace")
            headers = "".join(f"{k}: {v}\n" for k, v in resp.headers.items())
            return f"HTTP {resp.status} {url}\n{headers}\n{text}"
    except urllib.error.HTTPError as e:
        text = e.read(8192).decode("utf-8", "replace")
        return f"HTTP {e.code} {url}\n{text}"
    except urllib.error.URLError as e:
        return f"ERROR: could not reach {url}: {e.reason}"


def pg_query(sql: str, user: Optional[str] = None, password: Optional[str] = None) -> str:
    """Run a single SQL statement against the lab PostgreSQL DB and return the rows.

    Defaults to the gray-box app account from config. Pass user/password to try
    other credentials (e.g. when testing for weak/default logins).
    """
    config.assert_allowed(config.TARGET_HOST)
    if psycopg is None:
        return "ERROR: psycopg is not installed. Run: pip install 'psycopg[binary]'"
    user = user or config.DB_APP_USER
    password = password if password is not None else config.DB_APP_PASSWORD
    try:
        with psycopg.connect(
            host=config.TARGET_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
            user=user, password=password, connect_timeout=10,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description is None:
                    return f"OK (no rows). rowcount={cur.rowcount}"
                cols = [d.name for d in cur.description]
                rows = cur.fetchmany(50)  # cap output so we don't flood context
                lines = [" | ".join(cols)]
                lines += [" | ".join(str(c) for c in r) for r in rows]
                more = "" if cur.rowcount <= 50 else f"\n... ({cur.rowcount} rows total, showing 50)"
                return "\n".join(lines) + more
    except Exception as e:  # noqa: BLE001 -- surface the DB error text to the agent
        return f"DB ERROR as user {user!r}: {type(e).__name__}: {e}"


# --- Tool registry: schemas (for Claude) + dispatch (for us) ----------------
# The schema is how Claude learns what a tool does and what arguments it takes.
# Keep the descriptions clear -- the model relies on them to choose correctly.

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
]

DISPATCH = {
    "recon_nmap": recon_nmap,
    "http_probe": http_probe,
    "pg_query": pg_query,
}
