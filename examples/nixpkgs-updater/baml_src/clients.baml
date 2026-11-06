// GPT-6 Luna through OpenRouter. The key comes from OPENROUTER_API_KEY at
// request time. OPENROUTER_BASE_URL is only set by the offline tests, which
// point it at a local stub; unset, the client uses OpenRouter itself.
client OpenRouterLuna = openai.OpenRouterClient.new(
    model = "openai/gpt-6-luna",
    base_url = env.OPENROUTER_BASE_URL,
);
