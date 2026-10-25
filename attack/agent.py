"""
The agent is basically a loop that uses the intelligence of Claude in the cloud.

    1. Each time through the loops the agent sends Claude the current step in the goal, the context of what
       has already happened, and what tools are available for the next step.
    2. Claude does the "thinking" and responds. If it wants a tool, stop_reason == "tool_use".
    3. The agent runs the tool(s) it asked for and append the results for the next loop's context.
    4. Loop until Claude stops asking for tools (stop_reason == "end_turn")
       or we hit MAX_STEPS (so we don't waste money).

Example:  python agent.py "Map the lab, confirm PostgreSQL is reachable, and
                           report what the app account can see."

(Note: To work, you need to be sure you have API connectivity to Claude using the key I provided
"""

import sys
import anthropic

import config
import tools
from logbook import LogBook
from report_generator import generate_html_report

MAX_STEPS = 20  # limit so we don't go broke

"""
The SYSTEM definition is critical to make sure Claude doesn't 
go rogue, get confused, or hallucinate. 

The first paragraph is critical so that Claude doesn't block us as a real attacker
The second paragraph gives it the job to be done
The third paragraph gives it the key steps - just we talked about in class
The final paragraph tells it the kind of reporting we want
"""

SYSTEM = """You are an assistant on an AUTHORIZED, self-contained security lab
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


def run(goal):
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY (or an `ant auth login` profile)
    log = LogBook(config.LOG_PATH)
    log.run_start(goal=goal, target=config.DB_HOST, model=config.MODEL)

    # Array of dictionary types (key-value pairs) so we can have the full context each time
    messages = [{"role": "user", "content": goal}]

    for step in range(MAX_STEPS):
	# This is the key part - when we actually call Claude (this is the Claude API)
	# Arg1 - which Claude model to use (claude-haiku-4-5 in our case)
 	# Arg2 - Max tokens - again, just to make sure it doesn't go crazy
	# Arg3 - The guideline we made above
	# Arg4 - Our hacking functions that Claude can call (remember Claude and the agent aren't making them)
	# Arg5 - The history of the conversation for context
	# return - Claude's response
        resp = client.messages.create(
            model=config.MODEL,
            max_tokens=8000,
            system=SYSTEM,
            tools=tools.TOOL_SCHEMAS,
            messages=messages,
        )

        # Record and show any text Claude produced this turn.
	# The resp from Claude is an object. 
	# The structure:
	# stop_reason - why Claude stopped computing - either "tool_use" or "run_end"
	# content[] - text that explains what is happening
        for data in resp.content:
            if data.type == "text":
                log.model_text(step=step, text=data.text) 

        # Append Claude's full turn to the history (required for the next call).
        messages.append({"role": "assistant", "content": resp.content})

	# It's done 
        if resp.stop_reason != "tool_use":
            log.run_end(step=MAX_STEPS, stop_reason="max_steps")
            print("\n=== agent finished ===")
            # Generate HTML report
            report_path = generate_html_report(config.LOG_PATH)
            print(f"Report saved: {report_path}")
            return

	# Run every tool Claude asked for, collect results into one user turn.
        results = []
        for data in resp.content:
	    # Sometimes Claude sent things that we didn't need to do
            if data.type != "tool_use":
                continue
            log.tool_call(step=step, tool=data.name, tool_input=data.input)
 
            # Dispatch by tool name. Each branch pulls the arguments Claude chose
            # out of data.input (a dict) and passes them explicitly. Required
            # args use data.input["x"]; optional args use data.input.get("x").
            # NOTE: when you add a tool (see EXTENDING.md), add a branch here too.
            if data.name == "recon_nmap":
                output = tools.recon_nmap(ports=data.input.get("ports", "1-10000"))
            elif data.name == "http_probe":
                output = tools.http_probe(path=data.input["path"], method=data.input.get("method", "GET"),body=data.input.get("body"))
            elif data.name == "pg_query":
                output = tools.pg_query(sql=data.input["sql"], user=data.input.get("user"),password=data.input.get("password"))
            else:
                output = f"ERROR: unknown tool {data.name}"
 
            log.tool_result(step=step, tool=data.name, output=output)
            results.append({
                "type": "tool_result",
                "tool_use_id": data.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})


    log.record("run_end", step=MAX_STEPS, stop_reason="max_steps")
    print("\n=== hit MAX_STEPS; stopping ===")
    # Generate HTML report
    report_path = generate_html_report(config.LOG_PATH)
    print(f"Report saved: {report_path}")

def main():
    goal = sys.argv[1]
    run(goal)

main()
