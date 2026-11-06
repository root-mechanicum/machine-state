import { Type } from "@sinclair/typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { homedir } from "node:os";
import { join } from "node:path";

// This interface is deliberately narrower than cap act. The broker checks
// the same restrictions again; the model never gets a shell or arbitrary file tools.
export default function (pi: ExtensionAPI) {
  const cap = join(homedir(), "src/machine-state/bin/cap");
  pi.registerTool({
    name: "cap_list",
    label: "Find workstation observations",
    description: "List available read-only workstation observations and their arguments.",
    parameters: Type.Object({}),
    async execute() {
      const r = await pi.exec(cap, ["list", "--json"], { timeout: 30000 });
      if (r.code !== 0) throw new Error(r.stderr || "cap list failed");
      const entries = JSON.parse(r.stdout).filter((a: any) =>
        a.available && !a.mutating && a.consequence === "observe" &&
        !a.action.startsWith("agent.") &&
        // Only context reads; the broker (cap observe) checks the same again.
        (a.channels || []).every((c: string) => c === "desktop:read" || c === "browser:read"),
      ).map((a: any) => ({ action: a.action, label: a.label, args: a.args }));
      return { content: [{ type: "text", text: JSON.stringify(entries) }], details: {} };
    },
  });
  pi.registerTool({
    name: "cap_observe",
    label: "Observe workstation",
    description: "Run one observation from cap_list. Arguments must be declared by that action.",
    parameters: Type.Object({
      action: Type.String({ description: "Action name from cap_list" }),
      args: Type.Optional(Type.Record(Type.String(), Type.String(), { description: "Action arguments" })),
    }),
    async execute(_id, params) {
      const args = Object.entries(params.args || {}).map(([k, v]) => `${k}=${v}`);
      const r = await pi.exec("env", ["CAP_CALLER=agent", cap, "observe", params.action, ...args], { timeout: 30000 });
      if (r.code !== 0) throw new Error(r.stderr || r.stdout || "observation failed");
      return { content: [{ type: "text", text: r.stdout }], details: {} };
    },
  });
}
