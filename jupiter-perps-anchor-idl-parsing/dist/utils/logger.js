/* eslint-disable no-console */
// Fancy, emoji-forward console logger for quick diagnosis.
export const bar = (title, emoji = "🧭") => {
    const line = "─".repeat(Math.max(12, 62 - title.length));
    console.log(`\n${line} ${emoji}  ${title}  ${emoji} ${line}`);
};
export const info = (emoji, msg) => console.log(`${emoji}  ${msg}`);
export const ok = (msg) => console.log(`✅  ${msg}`);
export const warn = (msg) => console.log(`⚠️  ${msg}`);
export const fail = (msg) => console.error(`🛑  ${msg}`);
export const kv = (label, value) => {
    const l = label.padEnd(18, " ");
    console.log(`  • ${l} = ${value}`);
};
export const fmtPk = (x) => x ? (x.toBase58().slice(0, 4) + "…" + x.toBase58().slice(-4)) : "(none)";
//# sourceMappingURL=logger.js.map