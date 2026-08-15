import { describe, expect, it, vi } from "vitest";
import { validateResumeLlmCredential } from "./resumeLlmConfig";

describe("resume LLM credential validation", () => {
  it("calls the provider's lightweight models endpoint with the secret only when configured", async () => {
    const priorKey = process.env.RESUME_LLM_API_KEY;
    const priorBaseUrl = process.env.RESUME_LLM_BASE_URL;
    process.env.RESUME_LLM_API_KEY = "test-server-only-key";
    process.env.RESUME_LLM_BASE_URL = "https://llm.example.test/v1";
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });

    await expect(validateResumeLlmCredential(fetchMock as unknown as typeof fetch)).resolves.toEqual({
      valid: true,
      skipped: false,
      reason: undefined,
    });
    expect(fetchMock).toHaveBeenCalledWith("https://llm.example.test/v1/models", {
      headers: { Authorization: "Bearer test-server-only-key" },
    });

    if (priorKey === undefined) delete process.env.RESUME_LLM_API_KEY;
    else process.env.RESUME_LLM_API_KEY = priorKey;
    if (priorBaseUrl === undefined) delete process.env.RESUME_LLM_BASE_URL;
    else process.env.RESUME_LLM_BASE_URL = priorBaseUrl;
  });
});

