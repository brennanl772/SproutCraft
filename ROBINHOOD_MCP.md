# Robinhood Trading MCP

This repo is configured to use Robinhood's official Trading MCP server, which
lets an AI agent read your Robinhood accounts and place equity trades in a
dedicated, separately-funded **Agentic** account.

- **Endpoint:** `https://agent.robinhood.com/mcp/trading`
- **Transport:** HTTP
- **Auth:** Robinhood OAuth (browser-based; your agent never sees your password)
- **Config:** [`.mcp.json`](./.mcp.json)

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

## Using it locally (recommended)

The OAuth handshake is interactive, so trading is best driven from **local**
Claude Code (CLI or desktop):

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

On first tool call, approve access in your browser. Order placement is
restricted to a dedicated Robinhood Agentic account that you fund separately;
read access (positions, balances, orders, transactions) spans your accounts.

## Using it in Claude Code on the web

Web/remote sessions run behind a network egress allowlist, so a server added
via `.mcp.json` is reached **directly** and gets blocked:

```
403  x-deny-reason: host_not_allowed
Host not in allowlist: agent.robinhood.com
```

Two ways to resolve it:

### Option A — Enable as a session connector (no allowlist needed)
Enable the Robinhood MCP as a **connector** on the session/routine. Connector
traffic routes through Anthropic's servers, so no egress change is required.

### Option B — Add the host to the environment's egress allowlist
1. At **claude.ai/code**, click the **cloud icon** and open the environment for editing.
2. Set **Network access** to **Custom**.
3. In **Allowed domains**, add `agent.robinhood.com` (one per line).
4. Check **"Also include default list of common package managers"**.
5. **Save**, then start a **new** session (changes apply to new containers).

> Note: OAuth still can't complete in a headless remote container even with the
> host allowed — use local Claude Code to actually place trades.

## References
- https://robinhood.com/us/en/agentic-trading/
- https://code.claude.com/docs/en/claude-code-on-the-web#network-access
