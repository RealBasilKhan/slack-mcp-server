#!/bin/sh
# Local stdio setup. Never installs dependencies, grants access, or sends messages.
set -eu

fail() { printf '%s\n' "$1" >&2; exit 1; }

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${SLACK_MCP_BINARY:-"$repo_dir/build/slack-mcp-server"}
[ -x "$binary" ] || fail 'Slack MCP binary is missing. Build it separately before activation.'

# A positive allowlist is mandatory, even when upstream permits unrestricted posting.
allowlist=${SLACK_MCP_ADD_MESSAGE_TOOL:-}
[ -n "$allowlist" ] || fail 'Set SLACK_MCP_ADD_MESSAGE_TOOL to the approved channel IDs.'
case "$allowlist" in
  *[!A-Z0-9,]*) fail 'Posting requires channel IDs on one line, with no spaces or control characters.' ;;
esac
printf '%s\n' "$allowlist" | LC_ALL=C grep -Eq '^[CDG][A-Z0-9]{8,}(,[CDG][A-Z0-9]{8,})*$' ||
  fail 'Posting requires a comma-separated list of channel IDs; unrestricted values are rejected.'

token=${SLACK_MCP_XOXP_TOKEN:-}
[ -n "$token" ] || fail 'Provide SLACK_MCP_XOXP_TOKEN through private configuration; see docs/lvrg-codex-setup.md.'
case "$token" in xoxp-*) ;; *) fail 'A non-rotating user OAuth token is required for this setup.' ;; esac
case "$token" in *[!A-Za-z0-9-]*) fail 'The OAuth token must be a single value with no spaces or shell statements.' ;; esac

umask 077
state_dir=${SLACK_MCP_STATE_DIR:-"${XDG_DATA_HOME:-$HOME/.local/share}/lvrg-slack-mcp"}
mkdir -p -- "$state_dir"
export SLACK_MCP_XOXP_TOKEN="$token"
export SLACK_MCP_ADD_MESSAGE_TOOL="$allowlist"
export SLACK_MCP_ENABLED_TOOLS='channels_list,conversations_history,conversations_replies,conversations_search_messages,conversations_add_message'
export SLACK_MCP_USERS_CACHE="$state_dir/users-cache.json"
export SLACK_MCP_CHANNELS_CACHE="$state_dir/channels-cache.json"
export SLACK_MCP_LOG_LEVEL=warn
export SLACK_MCP_ADD_MESSAGE_MARK=false
export SLACK_MCP_ADD_MESSAGE_UNFURLING=false
unset SLACK_MCP_XOXC_TOKEN SLACK_MCP_XOXD_TOKEN SLACK_MCP_XOXB_TOKEN
exec "$binary" --transport stdio
