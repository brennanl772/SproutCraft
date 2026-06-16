# SproutCraft — Robinhood Trading MCP

Clean slate. This repo registers Robinhood's official **trading MCP server** so a
Claude Code agent can read your account and place trades through Robinhood's own
sanctioned interface.

The server is declared in [`.mcp.json`](.mcp.json):

```json
{
  "mcpServers": {
    "robinhood-trading": {
      "type": "http",
      "url": "https://agent.robinhood.com/mcp/trading"
    }
  }
}
```

## ⚠️ It won't connect until you do three things

This is a managed Claude Code on the web environment, so registering the server
in `.mcp.json` is necessary but not sufficient:

1. **Allowlist the host.** `agent.robinhood.com` is currently **blocked** by this
   environment's network egress policy (verified: `403 Host not in allowlist`).
   Add `agent.robinhood.com` to the environment's **network egress** settings.
   See the network docs: https://code.claude.com/docs/en/claude-code-on-the-web
2. **Restart the session** so the new `.mcp.json` server is loaded.
3. **Authenticate.** Complete Robinhood's login/OAuth when the MCP prompts. This
   links *your* Robinhood account; credentials never go in this repo or chat.

If you're instead running the **Claude Code CLI on your own machine**, you can
register it there with:

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

## After it connects

Once the server is reachable and authenticated, the agent can discover the
Robinhood trading tools and, with safety rails, help you trade:

- **Read-only first** — check account, buying power, and positions before any order.
- **Tiny size** to start, and **explicit confirmation before every live order**.
- Real money is at risk the moment orders are live — start small.

> Not financial advice. You are responsible for any trades placed on your account.
