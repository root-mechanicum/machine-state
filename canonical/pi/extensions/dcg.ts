import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type GuardDecision = { decision?: string };

async function check(pi: ExtensionAPI, command: string, cwd: string): Promise<{ allowed: boolean; reason: string }> {
  try {
    const result = await pi.exec(
      "dcg",
      ["test", "--robot", "--dialect", "posix", "--no-suggestions", command],
      { cwd, timeout: 5000 },
    );
    if (result.code !== 0) return { allowed: false, reason: `dcg failed closed (exit ${result.code})` };
    const parsed = JSON.parse(result.stdout) as GuardDecision;
    if (parsed.decision === "allow") return { allowed: true, reason: "" };
    return { allowed: false, reason: `dcg decision: ${parsed.decision ?? "indeterminate"}` };
  } catch (error) {
    return { allowed: false, reason: `dcg execution error: ${String(error)}` };
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event) => {
    if (event.toolName !== "bash") return;
    const command = typeof event.input.command === "string" ? event.input.command : "";
    const decision = await check(pi, command, process.cwd());
    return decision.allowed ? undefined : { block: true, terminate: true, reason: decision.reason };
  });

  // Pi exposes this event in current releases. Returning a result blocks denied user commands;
  // allowed commands continue through Pi's normal user-bash path.
  pi.on("user_bash", async (event) => {
    const decision = await check(pi, event.command, event.cwd);
    if (decision.allowed) return undefined;
    return {
      result: {
        output: `Command blocked: ${decision.reason}`,
        exitCode: 1,
        cancelled: false,
        truncated: false,
      },
    };
  });
}
