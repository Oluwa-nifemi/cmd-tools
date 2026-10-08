"""Agent profile for patterns.py. Copy to <audit_dir>/profile.py and edit for this agent.

patterns.py loads <audit_dir>/profile.py automatically. Both names are optional; the
defaults below treat every tool call as itself.
"""

# Tools that only format, link, or chart data the model already has. Turns that call
# only these tools count as presentation_only_turns. Leave empty if the agent has none.
PRESENTATION_TOOLS: set = set()


def tools_in_call(span: dict) -> set:
    """Return the tool names one top-level tool call ran.

    Called only for top-level calls that have no nested tool spans. Override it when a
    tool runs other tools without logging them as spans, for example a code tool whose
    input holds code, or a router tool whose input names the real tool. Return an empty
    set when the call ran no tool; patterns.py counts that as empty_tool_calls.

    span keys: name, input (JSON text, may be truncated), output_head, output_chars,
    duration_s, status, turn.
    """
    return {span["name"]}


# Example override for a code tool that calls tool functions from Python code:
#
# import ast, builtins, json
#
# def tools_in_call(span: dict) -> set:
#     if span["name"] != "execute_code":
#         return {span["name"]}
#     try:
#         tree = ast.parse(json.loads(span["input"])["code"])
#     except (ValueError, KeyError, SyntaxError):
#         return {span["name"]}
#     called = set()
#     for node in ast.walk(tree):
#         if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
#             called.add(node.func.id)
#     return called - set(dir(builtins))
