# Tool Context Manager

Installable Open WebUI Filter Function (experimental v0.1.0).

Target: Open WebUI v0.12.0. Pure Python, ARM64/aarch64 and x86-64.

## Install
1. Open Workspace > Functions and create a Filter Function.
2. Paste the contents of `tool_context_manager.py` and save.
3. Enable the filter globally or on the selected model.
4. Set `tool_token_threshold` (default 20000 estimated tokens), `keep_recent_groups` (default 2), and `enabled`.
5. To force compaction on demand, enable the per-user `force_compaction` valve, send a message, then turn the valve off.

## Scope and limitations
- Uses the `request()` hook, including tool-loop rounds when supported by the host.
- Summaries are deterministic extracts with truncated results, not model-generated semantic summaries.
- Does not change saved chat records; transforms the outgoing model request only.
- Threshold uses an approximate token count, not the model tokenizer.
- No slash command or one-click Action Function in this initial release.
- Does not persist compaction checkpoints. Later requests may recompact the same original tool history.
- Native general compaction may run independently; summary persistence through native compaction is not guaranteed.
- Leaves incomplete or nonstandard tool-call groups alone.
- Not yet integration-tested against a running Open WebUI v0.12.0 instance.

## Security
Tool outputs are untrusted data. This plugin makes no network calls, uses no architecture-specific libraries, and requires no new packages beyond Open WebUI's Pydantic dependency.

## Publishing
No personal identifiers, paths, hardware names, or credentials are included. Review Git commit author metadata and repository account identity before publishing.
