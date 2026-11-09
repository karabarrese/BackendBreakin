"""
Generate a pretty HTML report from a logfile.
Run after an agent completes to inspect the full trace.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def generate_html_report(logbook_path, output_path=None):
    """Read a logbook JSONL file and generate an HTML report."""
    if output_path is None:
        output_path = logbook_path.replace(".jsonl", ".html")

    # Read all log entries
    entries = []
    with open(logbook_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    # Group entries by step
    steps = {}
    metadata = {}
    for entry in entries:
        kind = entry.get("kind")
        step = entry.get("step", -1)

        if kind == "run_start":
            metadata = entry
        elif kind == "run_end":
            metadata["end_reason"] = entry.get("stop_reason")
        elif step >= 0:
            if step not in steps:
                steps[step] = {"reasoning": [], "tools": []}
            if kind == "model_text":
                steps[step]["reasoning"].append(entry["text"])
            elif kind == "tool_call":
                steps[step]["tools"].append({
                    "name": entry["tool"],
                    "input": entry["input"],
                    "call": entry,
                })
            elif kind == "tool_result":
                if steps[step]["tools"]:
                    steps[step]["tools"][-1]["output"] = entry["output"]

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Database Breach Lab Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        header {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #38bdf8;
            margin-bottom: 10px;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            font-size: 14px;
        }}
        .metadata-item {{
            background: rgba(51, 65, 85, 0.5);
            padding: 8px 12px;
            border-radius: 4px;
        }}
        .metadata-label {{
            color: #94a3b8;
            font-weight: 500;
        }}
        .metadata-value {{
            color: #e2e8f0;
            margin-top: 2px;
            font-family: monospace;
        }}
        .step {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .step-number {{
            color: #38bdf8;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .reasoning {{
            background: rgba(51, 65, 85, 0.3);
            border-left: 3px solid #10b981;
            padding: 12px 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }}
        .tool {{
            margin-bottom: 15px;
            background: rgba(51, 65, 85, 0.2);
            border-radius: 4px;
            overflow: hidden;
        }}
        .tool-header {{
            background: rgba(251, 146, 60, 0.1);
            border-left: 3px solid #fb923c;
            padding: 10px 15px;
            font-weight: 500;
            color: #fb923c;
        }}
        .tool-input, .tool-output {{
            padding: 12px 15px;
            background: rgba(30, 41, 59, 0.6);
            border-top: 1px solid rgba(51, 65, 85, 0.5);
        }}
        .tool-input-label, .tool-output-label {{
            color: #94a3b8;
            font-size: 12px;
            margin-bottom: 5px;
        }}
        pre {{
            background: rgba(15, 23, 42, 0.9);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
            color: #a1f717;
        }}
        .sql {{
            color: #60a5fa;
        }}
        .result-table {{
            width: 100%;
            background: rgba(15, 23, 42, 0.9);
            color: #e2e8f0;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .error {{
            color: #ff6b6b;
        }}
        footer {{
            text-align: center;
            color: #64748b;
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Database Breach Lab Report</h1>
            <div class="metadata">
                <div class="metadata-item">
                    <div class="metadata-label">Goal</div>
                    <div class="metadata-value">{metadata.get('goal', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Target</div>
                    <div class="metadata-value">{metadata.get('target', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Model</div>
                    <div class="metadata-value">{metadata.get('model', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Result</div>
                    <div class="metadata-value">{metadata.get('end_reason', 'N/A')}</div>
                </div>
            </div>
        </header>

        <div class="steps">
"""

    # Add steps
    for step_num in sorted(steps.keys()):
        step_data = steps[step_num]
        html += f"""
        <div class="step">
            <div class="step-number">Step {step_num}</div>
"""

        # Add reasoning
        for reasoning in step_data["reasoning"]:
            html += f"""
            <div class="reasoning">
                {reasoning}
            </div>
"""

        # Add tool calls
        for tool_data in step_data["tools"]:
            tool_name = tool_data["name"]
            tool_input = tool_data["input"]
            tool_output = tool_data.get("output", "")

            html += f"""
            <div class="tool">
                <div class="tool-header">→ {tool_name}</div>
"""

            # Format input based on tool type
            if tool_name == "pg_query":
                sql = tool_input.get("sql", "")
                user = tool_input.get("user", "")
                html += f"""
                <div class="tool-input">
                    <div class="tool-input-label">SQL Query (as {user}):</div>
                    <pre><span class="sql">{sql}</span></pre>
                </div>
"""
            else:
                html += f"""
                <div class="tool-input">
                    <div class="tool-input-label">Input:</div>
                    <pre>{json.dumps(tool_input, indent=2)}</pre>
                </div>
"""

            # Format output
            if tool_output:
                is_error = tool_output.startswith("ERROR")
                html += f"""
                <div class="tool-output">
                    <div class="tool-output-label">Result:</div>
                    <div class="result-table {'error' if is_error else ''}">{tool_output[:2000]}</div>
                </div>
"""

            html += """
            </div>
"""

        html += """
        </div>
"""

    html += """
        </div>

    </div>
</body>
</html>
"""

    # Write HTML
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <logbook.jsonl> [output.html]")
        sys.exit(1)

    logbook = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    result = generate_html_report(logbook, output)
    print(f"✓ Report generated: {result}")
