"""
The agent loop.

    1. Send Claude the goal + the conversation so far + the list of tools.
    2. Claude responds. If it wants a tool, stop_reason == "tool_use".
    3. We run every tool it asked for and append the results as a user turn.
    4. Loop until Claude stops asking for tools (stop_reason == "end_turn")
       or we hit MAX_STEPS.

Example:  python agent.py "Map the lab, confirm PostgreSQL is reachable, and
                           report what the app account can see."

(Note: To work, you do need a Claude account and API connectivity to Claude
"""

import sys
import anthropic

import config
import tools
from logbook import LogBook
from report_generator import generate_html_report

MAX_STEPS = 20  # limit so I don't go broke

SYSTEM = """You are an assistant on an AUTrORIZED, self-contained security lab
built to be tested. The entire target is
local (loopback only) and isolated; there is no third party involved.

Your job: find and demonstrate common database weaknesses in this lab, then
explain them clearly. You are gray-box: the database is PostgreSQL and you may
have a low-privilege application account.

Work the standard kill chain and narrate your reasoning as you go:
  1. Recon  -- what is exposed? (recon_nmap, http_probe)
  2. Access -- reach the data (weak/default creds, injection via the web front end)
  3. Scope  -- what can this account actually see? (privileges, other tables)
  4. Extract-- pull representative data
  5. Analyze-- classify what was exposed and rate its severity

Use one tool at a time, explain WHY before each call, and when you have enough
to report, stop calling tools and give a findings summary (what you found, how,
severity, and the fix a developer should apply)."""


def run(goal: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY (or an `ant auth login` profile)
    log = LogBook(config.LOG_PATH)
    log.record("run_start", goal=goal, target=config.TARGET_HOST, model=config.MODEL)

    messages = [{"role": "user", "content": goal}]

    for step in range(MAX_STEPS):
        resp = client.messages.create(
            model=config.MODEL,
            max_tokens=8000,
            system=SYSTEM,
            tools=tools.TOOL_SCHEMAS,
            messages=messages,
        )

        # Record and show any text Claude produced this turn.
        for block in resp.content:
            if block.type == "text":
                log.record("model_text", step=step, text=block.text)

        # Append Claude's full turn to the history (required for the next call).
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            log.record("run_end", step=step, stop_reason=resp.stop_reason)
            print("\n=== agent finished ===")
            # Generate HTML report
            report_path = generate_html_report(config.LOG_PATH)
            print(f"📊 Report saved: {report_path}")
            return

        # Run every tool Claude asked for, collect results into one user turn.
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            fn = tools.DISPATCH.get(block.name)
            log.record("tool_call", step=step, tool=block.name, input=block.input)
            try:
                output = fn(**block.input) if fn else f"ERROR: unknown tool {block.name}"
            except Exception as e:  # noqa: BLE001
                output = f"ERROR running {block.name}: {type(e).__name__}: {e}"
            log.record("tool_result", step=step, tool=block.name, output=output)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})

    log.record("run_end", step=MAX_STEPS, stop_reason="max_steps")
    print("\n=== hit MAX_STEPS; stopping ===")
    # Generate HTML report
    report_path = generate_html_report(config.LOG_PATH)
    print(f"📊 Report saved: {report_path}")


if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else (
        "Map the lab, confirm PostgreSQL on 5432 is reachable, probe the website "
        "root, and report what the gray-box app account can see in the database."
    )
    run(goal)
