# Decision: OpenRouter model id for the demo

Date: 2026-11-05. Source: `GET https://openrouter.ai/api/v1/models`
(public, no key), 454 models listed.

**Model id: `openai/gpt-6-luna`**. "OpenAI: GPT-6 Luna", 1,050,000-token
context, $0.10 / $0.50 per million input/output tokens at the time of
checking.

David asked for `gpt-6-luna`. OpenRouter needs the vendor prefix, so the BAML
client uses `model "openai/gpt-6-luna"`. Related ids, for reference:
`openai/gpt-6-luna-pro`, the floating alias `~openai/gpt-luna-latest`, and
`:batch` variants (not used: the demo is interactive).
