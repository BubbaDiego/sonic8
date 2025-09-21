/* bridge/echo.ts

Minimal sanity-check: prove we can run TypeScript via pnpm dlx tsx,

and emit stable JSON the Python side can parse.
*/
const payload = {
ok: true,
emoji: "🧩",
msg: "TS bridge online",
node: process.version,
cwd: process.cwd(),
ts: new Date().toISOString()
};
console.log(JSON.stringify(payload));
