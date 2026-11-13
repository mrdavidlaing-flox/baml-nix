// Your local Claude Code CLI and its login (a Claude Pro/Max subscription
// or an API key): BAML runs `claude -p` with no tools and passes the
// UpdatePlan schema as --json-schema. updater/claude.py builds the same client
// at run time to pick the model, the executable and an empty working
// directory; this one is the default for direct calls.
client ClaudeCode = claude_code.ClaudeCodeClient.new(model = "sonnet");
