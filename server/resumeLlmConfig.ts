export function getResumeLlmConfig() {
  const apiKey = process.env.RESUME_LLM_API_KEY?.trim();
  const baseUrl = (process.env.RESUME_LLM_BASE_URL || "https://api.openai.com/v1").replace(/\/$/, "");

  return {
    apiKey,
    baseUrl,
    enabled: Boolean(apiKey),
  } as const;
}

export async function validateResumeLlmCredential(fetchImpl: typeof fetch = fetch) {
  const config = getResumeLlmConfig();
  if (!config.enabled || !config.apiKey) {
    return { valid: false, skipped: true, reason: "No LLM API key is configured." } as const;
  }

  const response = await fetchImpl(`${config.baseUrl}/models`, {
    headers: { Authorization: `Bearer ${config.apiKey}` },
  });

  return {
    valid: response.ok,
    skipped: false,
    reason: response.ok ? undefined : `LLM provider returned ${response.status}.`,
  } as const;
}
