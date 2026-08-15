import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { getDemoScreening, screenUploads } from "./resumeScreeningService";

describe("resume screening service", () => {
  it("ships a ranked, export-ready demo cohort of at least ten candidates", async () => {
    const report = await getDemoScreening();
    expect(report.meta.totalCandidates).toBeGreaterThanOrEqual(10);
    expect(report.candidates).toHaveLength(report.meta.totalCandidates);
    expect(report.candidates[0].score).toBeGreaterThanOrEqual(report.candidates[1].score);
    expect(report.candidates[0]).toMatchObject({ rank: 1, candidateName: expect.any(String), explanation: expect.any(String) });
  });

  it("rejects sessions with fewer than ten resumes before document processing begins", async () => {
    await expect(screenUploads(
      { filename: "role.txt", mimeType: "text/plain", contentBase64: Buffer.from("Data analyst role").toString("base64") },
      [],
    )).rejects.toThrow("Upload at least 10 resumes");
  });

  it("bridges one job description and ten DOCX resumes into ranked Python analysis", async () => {
    const root = process.cwd();
    execFileSync("python3", ["scripts/create_upload_fixtures.py"], { cwd: root });
    const fixtureDir = "/tmp/rooman-upload-fixtures";
    const toPayload = async (filename: string, mimeType: string) => ({
      filename,
      mimeType,
      contentBase64: (await readFile(path.join(fixtureDir, filename))).toString("base64"),
    });
    const report = await screenUploads(
      await toPayload("job_description.txt", "text/plain"),
      await Promise.all(Array.from({ length: 10 }, (_, index) => toPayload(`candidate_${String(index + 1).padStart(2, "0")}.docx`, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))),
    );
    expect(report.meta.totalCandidates).toBe(10);
    expect(report.candidates).toHaveLength(10);
    expect(report.candidates[0]).toMatchObject({ rank: 1, score: expect.any(Number), explanation: expect.any(String) });
  }, 30_000);
});
