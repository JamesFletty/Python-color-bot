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
- Alternatively, switch `api/ai_service.py` to use `OPENAI_API_KEY` with base_url `https://api.openai.com/v1` if the user provides an OpenAI key
- No code changes needed once credits are added — the key and SDK setup are correct
