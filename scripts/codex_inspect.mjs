import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { Codex } from "@openai/codex-sdk";


const OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    summary: { type: "string" },
    findings: {
      type: "array",
      items: { type: "string" },
      maxItems: 20,
    },
    references: {
      type: "array",
      items: {
        type: "object",
        properties: {
          path: { type: "string" },
          start_line: { type: "integer", minimum: 1 },
          end_line: { type: "integer", minimum: 1 },
          relevance: { type: "string" },
        },
        required: ["path", "start_line", "end_line", "relevance"],
        additionalProperties: false,
      },
      maxItems: 30,
    },
    files_inspected: {
      type: "array",
      items: { type: "string" },
      maxItems: 100,
    },
    limitations: {
      type: "array",
      items: { type: "string" },
      maxItems: 20,
    },
  },
  required: ["summary", "findings", "references", "files_inspected", "limitations"],
  additionalProperties: false,
};


function requiredString(value, name) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${name} is required`);
  }
  return value.trim();
}


async function main() {
  let rawInput = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    rawInput += chunk;
  }
  const input = JSON.parse(rawInput);
  const workingDirectory = requiredString(input.working_directory, "working_directory");
  const question = requiredString(input.question, "question");
  const repository = requiredString(input.repository, "repository");
  const commitSha = requiredString(input.commit_sha, "commit_sha");
  const apiKey = requiredString(process.env.OPENAI_API_KEY, "OPENAI_API_KEY");
  const runtimeHome = await mkdtemp(join(tmpdir(), "openfde-codex-home-"));
  const controller = new AbortController();
  const timeoutMs = Number(input.timeout_ms ?? 120000);
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const codex = new Codex({
    apiKey,
    env: {
      PATH: process.env.PATH ?? "",
      HOME: runtimeHome,
      CODEX_HOME: runtimeHome,
      TMPDIR: process.env.TMPDIR ?? tmpdir(),
      LANG: process.env.LANG ?? "en_US.UTF-8",
    },
  });

  try {
    const thread = codex.startThread({
      model: input.model ?? "gpt-5.6-terra",
      modelReasoningEffort: input.reasoning_effort ?? "medium",
      sandboxMode: "read-only",
      workingDirectory,
      networkAccessEnabled: false,
      webSearchMode: "disabled",
      approvalPolicy: "never",
      threadSource: "openfde-codebase-inspector",
    });
    const prompt = `You are OpenFDE's read-only codebase inspector.

Repository: ${repository}
Commit: ${commitSha}
Manager question: ${question}

Inspect only the checked-out repository. Do not edit, create, delete, rename, or
format files. Do not make commits, pushes, or pull requests. Do not use the
network or speculate from outside knowledge. Use repository-relative paths and
exact 1-based line ranges for every reference. Verify line numbers directly
before citing them. Distinguish verified findings from limitations. Never read
or report credentials, tokens, private keys, .env files, or secret stores.

Return a concise evidence packet that another agent can use to write a grounded
answer. If the repository does not establish an answer, say so in limitations.`;

    const result = await thread.run(prompt, {
      outputSchema: OUTPUT_SCHEMA,
      signal: controller.signal,
    });
    const parsed = JSON.parse(result.finalResponse);
    process.stdout.write(JSON.stringify(parsed));
  } finally {
    clearTimeout(timeout);
    await rm(runtimeHome, { recursive: true, force: true });
  }
}


main().catch((error) => {
  const message = error instanceof Error ? error.message : "Codex inspection failed";
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
