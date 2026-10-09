# Slack MCP fork

Keep upstream Slack behavior unchanged unless the task explicitly calls for an
API change. Never commit tokens, browser cookies, private channel IDs or receipts.
Workspace access rules remain authoritative; this fork does not bypass them.

Repository workflows live in [skills/README.md](skills/README.md). For a
user-authorized Slack message or Threasury follow-up, load
[Slack verified send](skills/slack-verified-send/SKILL.md). Setup examples are in
[Codex setup](docs/lvrg-codex-setup.md). Installing a skill does not activate the
connector or authorize sending a message.

Verify launcher changes offline with a fake binary before account activation.
Do not install dependencies, create credentials or send messages merely to test
setup. Preserve other contributors' changes and keep private configuration
outside this repository.
