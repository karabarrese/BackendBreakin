"""
Every action the agent takes (a tool call, its result, each thing the model
says) gets appended to a file, and printed to the terminal so you can watch the run live.
"""

import json
import os
import time

class LogBook:
    def __init__(self, path):
        self.path = path
	# Create the log directory
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Truncate at the start of each run so latest.jsonl is just this run.
        open(path, "w").close()

    def run_start(self, goal, target, model):
        self._write({"kind": "run_start", "goal": goal, "target": target, "model": model})

    def model_text(self, step, text):
        self._write({"kind": "model_text", "step": step, "text": text})

    def tool_call(self, step, tool, tool_input):
        self._write({"kind": "tool_call", "step": step, "tool": tool, "input": tool_input})

    def tool_result(self, step, tool, output):
        self._write({"kind": "tool_result", "step": step, "tool": tool, "output": output})

    def run_end(self, step, stop_reason):
        self._write({"kind": "run_end", "step": step, "stop_reason": stop_reason})

    # everything calls write
    def _write(self, entry) :
        #Stamp the time, append one line, and print it to the console.
        row = {"t": round(time.time(), 3)}
        row.update(entry)
        f = open(self.path, "a")
        f.write(json.dumps(row, default=str) + "\n")
        f.close()
        _show(entry)


def _show(e) -> None:
    kind = e.get("kind")
    if kind == "run_start":
        print("=" * 60)
        print("Database Breach Lab")
        print(f"Goal:   {e.get('goal', '')}")
        print(f"Target: {e.get('target', '')}")
        print(f"Model:  {e.get('model', '')}")
        print("=" * 60)
    elif kind == "model_text":
        print(f"\n[step {e.get('step')}] reasoning:")
        print(str(e.get("text", "")).strip())
    elif kind == "tool_call":
        print(f"\n-> tool call: {e.get('tool')}")
        print(f"   input: {json.dumps(e.get('input', {}), default=str)}")
    elif kind == "tool_result":
        out = str(e.get("output", ""))
        if len(out) > 500:
            out = out[:500] + " ..."
        print(f"<- result:\n{out}")
    elif kind == "run_end":
        print("\n" + "=" * 60)
        print(f"run ended: {e.get('stop_reason')}")
        print("=" * 60)
