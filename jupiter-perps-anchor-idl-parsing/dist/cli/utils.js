/* eslint-disable no-console */
import path from "path";
import { fileURLToPath } from "url";
import chalk from "chalk";
export async function readStdinJSON() {
    const chunks = [];
    const stdin = process.stdin;
    if (stdin.isTTY) {
        throw new Error("No JSON on stdin. Pipe a JSON payload.");
    }
    for await (const chunk of stdin)
        chunks.push(chunk);
    const raw = Buffer.concat(chunks).toString("utf8");
    try {
        return JSON.parse(raw);
    }
    catch (e) {
        throw new Error(`Invalid JSON on stdin: ${e.message}`);
    }
}
export function writeJSON(obj) {
    process.stdout.write(JSON.stringify(obj, null, 2) + "\n");
}
export function debugBlock(title, lines = []) {
    const pad = (s) => "  " + s;
    console.error(chalk.gray("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"));
    console.error(chalk.cyanBright(`┃ ${title}`));
    for (const line of lines)
        console.error(chalk.gray(pad(line)));
    console.error(chalk.gray("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"));
}
export function debugKV(title, kv) {
    const lines = Object.entries(kv).map(([k, v]) => `${chalk.white(k)}: ${chalk.gray(v)}`);
    debugBlock(title, lines);
}
export function resolveRepoPath(...p) {
    // dist/cli/perps.js -> back to repo root
    const here = path.dirname(fileURLToPath(import.meta.url));
    const repoRoot = path.resolve(here, "..", "..");
    return path.resolve(repoRoot, ...p);
}
export function prettyError(err, context) {
    const e = err;
    const name = e?.name ?? "Error";
    const msg = e?.message ?? String(err);
    const extra = e?.stack ? e.stack.split("\n").slice(1, 6).map((s) => s.trim()) : [];
    const rows = [
        `${chalk.red("✖")} ${chalk.bold(name)}: ${msg}`,
        ...(context ? Object.entries(context).map(([k, v]) => `${k}: ${v}`) : []),
        ...extra,
    ];
    debugBlock("CLI Error", rows);
}
export function sideToIdlEnum(side) {
    const s = (side || "").toLowerCase();
    if (s === "long")
        return { long: {} };
    if (s === "short")
        return { short: {} };
    throw new Error(`Invalid side: ${side}. Use "long" or "short".`);
}
//# sourceMappingURL=utils.js.map