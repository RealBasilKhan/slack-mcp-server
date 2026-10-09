# Codex and Threasury setup

This fork adds a local stdio launcher, setup examples and a verified-send workflow.
It keeps upstream Slack API behavior unchanged. The posting handler calls Slack's
`chat.postMessage` through its client and has no blanket ban on Slack Connect
channels. Slack membership, app approval, OAuth scopes and workspace rules still
decide which channels are accessible. External-channel posting remains unproven
until the approved app can post and read back a message there.

## Prepare account access

Use [the user-token app manifest](../examples/lvrg-slack-app-manifest.json) as the
starting point for a workspace-approved app. These are **user token scopes**, so
messages are sent as the authenticated user, not a bot. Channel history, search
and user lookup support message verification; `im:read` and `mpim:read` support
upstream channel-cache initialization. This profile does not create DMs, manage
groups, join channels or upload files.

History verification in this profile covers public and private channels. DM or
group-DM readback additionally requires the separately approved `im:history` or
`mpim:history` user scope, respectively. Those scopes are not included in this
Threasury channel setup. Do not send into a DM when its readback access is missing.

The upstream server accepts OAuth tokens; it does not offer a browser login
wizard, token storage service or automatic refresh. App creation, workspace
installation and token issuance require the account owner's approval. This
manifest disables token rotation because the server does not refresh rotating
tokens. If workspace policy requires rotation, this profile is unsuitable until
refresh support is implemented. Do not extract browser cookies as a workaround.

Keep the existing `xoxp-` token outside Git and inject `SLACK_MCP_XOXP_TOKEN`
through private client environment configuration. Shell config and `.env` files
are never sourced. Credentials are never included in examples.

## Prepare the runtime and configuration

1. Review the source and dependency lockfile. With approval to build/install, use
   Go 1.25 or newer and build `./cmd/slack-mcp-server` to
   `build/slack-mcp-server`. Building may download dependencies; the launcher does
   not build or install anything. `SLACK_MCP_BINARY` can name an existing binary.
2. Find the destination's actual channel ID through an authenticated channel
   listing. Confirm membership and whether the channel is externally shared.
   Put approved IDs in `SLACK_MCP_ADD_MESSAGE_TOOL`, separated by commas. The
   launcher rejects missing lists, `true`, `1` and exclusion lists.
3. Adapt [the Codex overlay example](../examples/lvrg-codex-overlay.json) in private
   configuration. Its channel ID and paths are placeholders, not account facts.
   In the shared LVRG setup, merge into
   `~/.config/mcp-servers/overlays/codex.json`, then run `agent-sync sync mcp`.
   Do not overwrite the full overlay or edit generated Codex MCP tables.
4. Restart the client and verify stdio initialization plus `tools/list`. Expect
   `channels_list`, `conversations_history`, `conversations_replies`,
   `conversations_search_messages` and `conversations_add_message` only.
5. Verify the target channel with bounded reads. Send only a message explicitly
   requested by the user, then follow [Slack verified send](../skills/slack-verified-send/SKILL.md).

Cache files go under `~/.local/share/lvrg-slack-mcp`, or an explicit
`SLACK_MCP_STATE_DIR`. Posting does not automatically mark the channel read or
unfurl links. In upstream, a mark-read error can occur after a successful send;
leaving that feature off avoids that additional ambiguous result.

## Threasury follow-up

The top-up workflow owns the amount, receipt, submission state and destination
channel. This connector handles the separately authorized Slack follow-up. Load
[Slack verified send](../skills/slack-verified-send/SKILL.md), check the recent
channel/thread for an existing follow-up, and use plain language. For example:
“Hi, I sent the top-up payment and uploaded the receipt. Please confirm when it
has been credited.” Only say the receipt was uploaded if that is verified.
Payment sent, receipt submitted and wallet credited are different facts.

Do not attach private receipts to this repository or send them automatically.
This profile supports text messages, not file upload. On an ambiguous result,
read back first and report uncertainty instead of sending a duplicate. An access
denial must be resolved through approved workspace access, not another identity
or an unrestricted token.
