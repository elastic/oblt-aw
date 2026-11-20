---
steps:
  # BEGIN synced-from:.python-version:setup-python
  - name: Setup Python
    # Control-plane pin (baked at compile time). Do not use
    # python-version-file here — agent jobs check out the consumer
    # repo, so .python-version would be the target's pin.
    uses: actions/setup-python@v7
    with:
      python-version: '3.14'
  # END synced-from:.python-version:setup-python

  - name: Setup Node.js (.node-version)
    if: hashFiles('.node-version') != ''
    uses: actions/setup-node@v7
    with:
      node-version-file: '.node-version'

  - name: Setup Node.js (.nvmrc)
    if: hashFiles('.node-version') == '' && hashFiles('.nvmrc') != ''
    uses: actions/setup-node@v7
    with:
      node-version-file: '.nvmrc'

  - name: Configure Copilot CLI settings
    shell: bash
    run: |
      set -euo pipefail
      mkdir -p ~/.copilot
      CONFIG="$HOME/.copilot/config.json"
      if [ -f "$CONFIG" ]; then
          jq '. + {"chat.customAgentInSubagent.enabled": true}' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
      else
          echo '{"chat.customAgentInSubagent.enabled":true}' > "$CONFIG"
      fi

  - name: Fetch repository conventions
    shell: bash
    run: |
      set -euo pipefail
      if [ -f "AGENTS.md" ]; then
        cp AGENTS.md /tmp/agents.md
        echo "Repository conventions copied from AGENTS.md to /tmp/agents.md"
      else
        echo "No AGENTS.md found; continuing without repository conventions"
      fi
---

Repository conventions are pre-fetched to `/tmp/agents.md`. Read this file early in your task to understand the codebase's conventions, guidelines, and patterns. If the file doesn't exist, continue without it. When spawning sub-agents, include the contents of `/tmp/agents.md` in each sub-agent's prompt (or tell the sub-agent to read the file directly).
