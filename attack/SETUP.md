	# Breach Lab — Setup Guide

	Go from a blank Mac to a running agent in about 10 minutes. This assumes you
	have **nothing** installed yet. Commands are copy-paste ready; run them in
	Terminal in order.

	> **What this is:** a self-contained security lab. It spins up a local
	> PostgreSQL database seeded with deliberate weaknesses (plaintext passwords,
	> secrets in a table, over-permissive grants), then lets a Claude-driven agent
	> discover and explain them. Everything runs on your own machine, loopback only
	> (`127.0.0.1`). It never touches anything outside your laptop — that's enforced
	> in code by an allowlist.

	---

	## 0. Install the tools (one time)

	**Homebrew** (the macOS package manager):

	```bash
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
	```

	When it finishes it prints two "Next steps" commands that add `brew` to your
	PATH — run them. On Apple Silicon they are:

	```bash
	echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
	eval "$(/opt/homebrew/bin/brew shellenv)"
	```

	Then install **Python**, **PostgreSQL**, and **nmap** 

	```bash
	brew install python postgresql@16 nmap
	```

	> Already have a different Postgres version (e.g. `postgresql@15`)? That's fine —
	> just use your version number everywhere you see `@16` below.

	---

	## 1. Start PostgreSQL

	```bash
	brew services start postgresql@16
	psql --version          # confirm it's on your PATH
	```

	If `psql` isn't found, run the `export PATH=...` line that `brew install`
	printed, or open a new Terminal window.

	---

	## 2. Get the project

	```bash
	cd ~
	git clone <your-repo-url> db_breach   # or copy the folder here
	cd db_breach
	```

	Set up an isolated Python environment and install the dependencies. The venv is
	required — Homebrew's Python blocks global `pip install`.

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	```

	You should now see `(.venv)` at the start of your prompt. **Re-run
	`source .venv/bin/activate` in every new Terminal window.**

	---

	## 3. Create the lab database

	```bash
	psql -d postgres -f setup_lab.sql
	```

	On Homebrew, your macOS username is already a Postgres superuser, so no
	`-U postgres` is needed. (If your install *does* have a `postgres` role, use
	`psql -U postgres -d postgres -f setup_lab.sql` instead.)

	You should see the script print the tables, users, and secrets it created. It's
	safe to re-run.

	---

	## 4. Add your Claude API key

	Get a key from the [Claude Console](https://console.anthropic.com/), then:

	```bash
	export ANTHROPIC_API_KEY=put-your-api-key-here
	```

	To avoid re-typing it every session, add that line to `~/.zshrc`.

	---

	## 5. Run the agent

	```bash
	python agent.py "Connect as app_user and list the tables."
	```

	You'll see the agent's live reasoning and tool calls in the terminal. When it
	finishes it writes a formatted report to **`runs/latest.html`** (open it in a
	browser) and a machine-readable log to **`runs/latest.jsonl`**.

	Try a few goals:

	```bash
	python agent.py "Retrieve all user data and report how passwords are stored."
	python agent.py "Check what the app_user account can and cannot access."
	python agent.py "Examine the audit_log table and report what activity is tracked."
	```

      ## 6. Print the Results

        ```bash
 	python3 results.py runs/latest.jsonl 
        ```

