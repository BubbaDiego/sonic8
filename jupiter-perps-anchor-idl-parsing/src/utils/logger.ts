/* eslint-disable no-console */
// Fancy, emoji-forward console logger for quick diagnosis.

export const bar = (title: string, emoji = "🧭") => {
  const line = "─".repeat(Math.max(12, 62 - title.length));
  console.log(`\n${line} ${emoji}  ${title}  ${emoji} ${line}`);
};

export const info = (emoji: string, msg: string) => console.log(`${emoji}  ${msg}`);
export const ok = (msg: string) => console.log(`✅  ${msg}`);
export const warn = (msg: string) => console.log(`⚠️  ${msg}`);
export const fail = (msg: string) => console.error(`🛑  ${msg}`);

export const kv = (label: string, value: unknown) => {
  const l = label.padEnd(18, " ");
  console.log(`  • ${l} = ${value}`);
};

export const fmtPk = (x: { toBase58(): string } | undefined | null) =>
  x ? (x.toBase58().slice(0, 4) + "…" + x.toBase58().slice(-4)) : "(none)";
