# Extending the Lab — Adding and Testing New Attacks

The agent can only do what we've given it tools for. Adding a new capability means
adding a new **tool**, and a tool is three things in `tools.py` and one in `agent.py`. 

> Keep every new tool that works directly with the DB loopback-only. 
> For the web-based SQL injection, we can use the website

---

## A tool is four parts

1. **A function** that does the work and returns a **string** (the agent reads
   strings, so summarize results as text).
2. **A schema** in `TOOL_SCHEMAS` — the name, a clear description, and its
   inputs. Claude chooses tools based on the description, so write it plainly.
3. **A dispatch entry** in `DISPATCH` mapping the name to the function.
4. **An entry** in agent.py in the if chain that calls the function

That's it. Claude discovers the new tool automatically the next run.
