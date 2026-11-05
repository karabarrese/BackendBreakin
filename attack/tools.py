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


# Tool registry to handle argument validation and reading tool calls
# required arguments use args["x"]; optional arguments use args.get("x")
# NOTE: when you add a tool, add a corresponding tool registry too

def _run_recon(args):
    return recon_nmap(
        ports=args.get("ports", "1-10000")
    )

def _run_http(args):
    return http_probe(
        path=args["path"],
        method=args.get("method", "GET"),
        body=args.get("body"),
    )

def _run_pg_query(args):
    return pg_query(
        sql=args["sql"],
        user=args.get("user"),
        password=args.get("password"),
    )

# Dispatch by tool name. Each function pulls the arguments Claude chose
# out of data.input (a dict) and passes them explicitly.
# Catches missing arguments, unknown tools, and general tool exceptions
def dispatch_tool(name, args):
    if not isinstance(args, dict):
        return "ERROR: tool arguments must be an object."
    
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"ERROR: unknown tool {name}"
    
    try:
        return handler(args)
    except KeyError as error:
        return f"ERROR: missing required argument: {error.args[0]}"
    except Exception as error:
        return f"ERROR: {type(error).__name__}: {error}"

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
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp = urllib.request.urlopen(req, timeout=20)
    text = resp.read(8192).decode("utf-8", "replace")
    headers = "".join(f"{k}: {v}\n" for k, v in resp.headers.items())
    return f"HTTP {resp.status} {url}\n{headers}\n{text}"


# Run one SQL statement against the lab database and return up to 50 rows.
# Defaults to the gray-box app account; pass user/password to try other creds.
def pg_query(sql, user=None, password=None):
    user = user or config.DB_APP_USER
    password = password if password is not None else config.DB_APP_PASSWORD

    with psycopg.connect(
        host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
        user=user, password=password, connect_timeout=10,
    ) as conn:
        cur = conn.cursor()
        cur.execute(sql)

        # INSERT/UPDATE and friends return no rows to display.
        if cur.description is None:
            return f"OK (no rows). rowcount={cur.rowcount}"

        cols = [d.name for d in cur.description]
        rows = cur.fetchmany(50)   # cap output so we don't flood the agent

    lines = [" | ".join(cols)]
    for r in rows:
        lines.append(" | ".join(str(c) for c in r))
    return "\n".join(lines)


# --- Tool schemas: how Claude learns what each tool does and what it takes ---
# Claude reads these descriptions to choose a tool, so keep them clear. When you
# add a tool, add its schema here AND a matching branch in agent.py (see
# EXTENDING.md).

# What Claude is allowed to request
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

# How Python executes each request
TOOL_HANDLERS = {
    "recon_nmap": _run_recon,
    "http_probe": _run_http,
    "pg_query": _run_pg_query,
}