---
name: xAI API key credits issue
description: The XAI_API_KEY secret is set but the team account has no credits, blocking AI endpoints
---

# xAI Credits Issue

**Why:** User created a new xAI team account and generated an API key, but did not add billing credits. The Grok API returns 403 permission-denied when no credits exist.

**Error message:** "Your newly created team doesn't have any credits or licenses yet."

**How to apply:**
- The secret `XAI_API_KEY` is correctly stored in Replit secrets
- The base URL `https://api.x.ai/v1` and OpenAI-compatible SDK setup is correct
- Credits can be added at: https://console.x.ai/
- `api/ai_service.py` now supports Azure OpenAI (preferred), direct OpenAI, and xAI.
- For Azure: set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and deployment names
  (`AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_TRANSLATE_DEPLOYMENT`).
- For OpenAI: set `OPENAI_API_KEY` (optional `AI_PROVIDER=openai`).
- xAI still works when credits are added and `XAI_API_KEY` is set.
