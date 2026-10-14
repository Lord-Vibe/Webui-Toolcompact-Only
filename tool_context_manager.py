"""
title: Tool Context Manager
author: Community Contributors
version: 0.1.0
description: Independent, request-scoped tool history compaction for Open WebUI.
requirements:
"""
import copy
import json
import math
from typing import Optional
from pydantic import BaseModel, Field

MARKER = "[Tool Context Manager summary]"
def estimate_tokens(value):
    """Conservative approximation; not provider tokenizer accounting."""
    return max(1, math.ceil(len(json.dumps(value, ensure_ascii=False, default=str)) / 3))

def text_of(value, limit=1000):
    if isinstance(value, str):
        return value[:limit]
    return json.dumps(value, ensure_ascii=False, default=str)[:limit]

def tool_groups(messages):
    """Only closed assistant tool-call groups with matching tool responses."""
    groups = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        calls = msg.get("tool_calls") if isinstance(msg, dict) else None
        if msg.get("role") != "assistant" or not isinstance(calls, list) or not calls:
            i += 1
            continue
        ids = [c.get("id") for c in calls if isinstance(c, dict)]
        if len(ids) != len(calls) or any(not x for x in ids):
            i += 1
            continue
        j = i + 1
        seen = set()
        while j < len(messages) and messages[j].get("role") == "tool":
            seen.add(messages[j].get("tool_call_id"))
            j += 1
        if set(ids) == seen and len(seen) == len(ids):
            groups.append((i, j))
            i = j
        else:
            i += 1
    return groups

def compact(body, threshold, keep_recent, force=False, preview_chars=450):
    messages = body.get("messages")
    if not isinstance(messages, list):
        return body, None
    groups = tool_groups(messages)
    total = sum(estimate_tokens(messages[a:b]) for a,b in groups)
    if not groups or (not force and total < threshold):
        return body, None
    eligible = groups[:-keep_recent] if keep_recent else groups
    if not eligible:
        return body, None
    # Extractive, bounded summaries. Avoid inventing results and avoid external calls.
    replacements = {}
    removed = set()
    for a,b in eligible:
        parts = []
        for call in messages[a].get("tool_calls", []):
            fn = call.get("function") or {}
            parts.append("Tool: " + str(fn.get("name", "unknown")) +
                         " | arguments: " + text_of(fn.get("arguments", ""), preview_chars))
        for msg in messages[a+1:b]:
            parts.append("Result (" + str(msg.get("tool_call_id")) + "): " +
                         text_of(msg.get("content", ""), preview_chars))
        replacements[a] = {"role": "system", "content": MARKER + "\n" + "\n".join(parts)}
        removed.update(range(a+1,b))
    result = copy.copy(body)
    result["messages"] = [replacements.get(i, msg) for i,msg in enumerate(messages) if i not in removed]
    before = estimate_tokens(messages)
    after = estimate_tokens(result["messages"])
    return result, {"tool_tokens_before": total, "request_tokens_before": before,
                    "request_tokens_after": after, "groups": len(eligible)}

class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0)
        enabled: bool = Field(default=True, description="Automatic tool-only compaction")
        tool_token_threshold: int = Field(default=20000, ge=100)
        keep_recent_groups: int = Field(default=2, ge=0)
        result_preview_chars: int = Field(default=450, ge=80, le=5000)
        notify: bool = Field(default=True)
    class UserValves(BaseModel):
        force_compaction: bool = Field(default=False, description="Manually compact tool history on each request while enabled")
    def __init__(self):
        self.valves = self.Valves()
    async def request(self, body: dict, __user__: Optional[dict] = None,
                      __event_emitter__=None) -> dict:
        try:
            user_valves = (__user__ or {}).get("valves") or {}
            force = bool(user_valves.get("force_compaction", False))
            if not self.valves.enabled and not force:
                return body
            output, stats = compact(body, self.valves.tool_token_threshold,
                                    self.valves.keep_recent_groups, force,
                                    self.valves.result_preview_chars)
            if stats and self.valves.notify and __event_emitter__:
                await __event_emitter__({"type": "status", "data": {
                    "description": "Tool context reduced: ~{} → ~{} request tokens ({} tool rounds)".format(
                        stats["request_tokens_before"], stats["request_tokens_after"], stats["groups"]),
                    "done": True}})
            return output
        except Exception:
            # Fail open: preserve original request.
            return body
