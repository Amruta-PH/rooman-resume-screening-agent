import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

export type UploadPayload = { filename: string; mimeType: string; contentBase64: string };
const MAX_FILE_BYTES = 3 * 1024 * 1024;
const JD_EXTENSIONS = new Set([".pdf", ".docx", ".txt"]);
const RESUME_EXTENSIONS = new Set([".pdf", ".docx"]);

function suffix(filename: string) { return path.extname(filename).toLowerCase(); }
function safeName(filename: string) { return path.basename(filename).replace(/[^a-zA-Z0-9._-]/g, "_"); }

function decodeUpload(file: UploadPayload, kind: "job description" | "resume") {
  const allowed = kind === "job description" ? JD_EXTENSIONS : RESUME_EXTENSIONS;
  if (!allowed.has(suffix(file.filename))) throw new Error(`Unsupported ${kind} '${file.filename}'. Accepted formats: ${Array.from(allowed).join(", ")}.`);
  const buffer = Buffer.from(file.contentBase64, "base64");
  if (!buffer.length) throw new Error(`'${file.filename}' is empty.`);
  if (buffer.length > MAX_FILE_BYTES) throw new Error(`'${file.filename}' exceeds the 3 MB size limit.`);
  return buffer;
}

export async function screenUploads(jobDescription: UploadPayload, resumes: UploadPayload[]) {
  if (resumes.length < 10) throw new Error("Upload at least 10 resumes to begin screening.");
  if (resumes.length > 30) throw new Error("For reliable analysis, screen no more than 30 resumes at one time.");
  const directory = await mkdtemp(path.join(tmpdir(), "rooman-screening-"));
  try {
    const jobBuffer = decodeUpload(jobDescription, "job description");
    const jobPath = path.join(directory, `job-description${suffix(jobDescription.filename)}`);
    await writeFile(jobPath, jobBuffer);
    const resumeEntries = await Promise.all(resumes.map(async (resume, index) => {
      const buffer = decodeUpload(resume, "resume");
      const filename = safeName(resume.filename);
      const destination = path.join(directory, `${index}-${filename}`);
      await writeFile(destination, buffer);
      return { path: destination, filename };
    }));
    const inputPath = path.join(directory, "input.json");
    await writeFile(inputPath, JSON.stringify({ job_path: jobPath, resumes: resumeEntries }));
    const output = await new Promise<string>((resolve, reject) => {
      const childProcess = spawn("python3", ["python_service/resume_analyzer.py", "--input", inputPath], { cwd: process.cwd(), env: process.env });
      let stdout = "", stderr = "";
      childProcess.stdout.on("data", (chunk: Buffer) => { stdout += chunk.toString(); });
      childProcess.stderr.on("data", (chunk: Buffer) => { stderr += chunk.toString(); });
      childProcess.on("error", () => reject(new Error("The document-analysis service could not be started. Please try again.")));
      childProcess.on("close", (code: number | null) => code === 0 ? resolve(stdout) : reject(new Error(stderr || JSON.parse(stdout || "{}").error || "The document-analysis service could not complete the request.")));
    });
    const result = JSON.parse(output);
    if (result.error) throw new Error(result.error);
    return result;
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

export async function getDemoScreening() {
  const data = await readFile(path.join(process.cwd(), "sample_data", "demo_screening_results.json"), "utf-8");
  return JSON.parse(data);
}
