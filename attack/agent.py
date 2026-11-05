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
    log = None
    current_step = 0
    run_ended = False

    try:
        log = LogBook(config.LOG_PATH)
        log.run_start(goal=goal, target=config.DB_HOST, model=config.MODEL)

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY (or an `ant auth login` profile)
        # Array of dictionary types (key-value pairs) so we can have the full context each time
        messages = [{"role": "user", "content": goal}]

        # This is the key part - when we actually call Claude (this is the Claude API)
        # Arg1 - which Claude model to use (claude-haiku-4-5 in our case)
        # Arg2 - Max tokens - again, just to make sure it doesn't go crazy
        # Arg3 - The guideline we made above
        # Arg4 - Our hacking functions that Claude can call (remember Claude and the agent aren't making them)
        # Arg5 - The history of the conversation for context
        # return - Claude's response
        for step in range(MAX_STEPS):
            current_step = step
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
                log.run_end(step=step, stop_reason=resp.stop_reason)
                run_ended = True
                print("\n=== agent finished ===")
                return

            # Run every tool Claude asked for, collect results into one user turn.
            results = []
            for data in resp.content:
                # Sometimes Claude sent things that we didn't need to do
                if data.type != "tool_use":
                    continue
                
                log.tool_call(
                    step=step,
                    tool=data.name,
                    tool_input=data.input,
                )
                    
                # Replaced original if elif chain with simpler function call that handles logic
                # Dispatch tool function makes sure
                output = tools.dispatch_tool(data.name, data.input)
                    
                log.tool_result(
                    step=step,
                    tool=data.name,
                    output=output,
                )
                
                results.append({
                    "type": "tool_result",
                    "tool_use_id": data.id,
                    "content": output,
                })
            
            messages.append({"role": "user", "content": results})


        log.run_end(step=current_step, stop_reason=resp.stop_reason)
        run_ended = True
        print("\n=== hit MAX_STEPS; stopping ===")
    except Exception as error:
        if log is not None and not run_ended:
            try:
                log.run_end(step=current_step, stop_reason="error")
            except Exception as logging_error:
                print(f"Unable to record run failure: {logging_error}")
        print(f"\n=== agent failed: {error} ===")
    finally:
        if log is not None:
            try:
                # Generate HTML report
                report_path = generate_html_report(config.LOG_PATH)
                print(f"Report saved: {report_path}")
            except Exception as report_error:
                print(f"Unable to generate HTML report: {report_error}")

def main():
    goal = sys.argv[1]
    run(goal)

main()
