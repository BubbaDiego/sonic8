// Print the account metas for a given instruction so we know
// whether an account must be a signer, writable, etc.
// Run:
//   TS_NODE_PROJECT=jupiter-perps-anchor-idl-parsing/tsconfig.json \
//     node --loader ts-node/esm \
//     jupiter-perps-anchor-idl-parsing/src/tools/dump_ix_accounts.ts createIncreasePositionMarketRequest

import { IDL } from "../idl/jupiter-perpetuals-idl.js";

const name = (process.argv[2] || "createIncreasePositionMarketRequest").toString();

const ix = (IDL as any).instructions?.find((i: any) => i?.name === name);
if (!ix) {
  console.error("Instruction not found:", name);
  process.exit(1);
}
console.log("Instruction:", ix.name);
console.log(
  "Args:",
  ix.args?.map(
    (a: any) => `${a.name}:${a.type?.defined || a.type?.option || a.type?.array || a.type || "unknown"}`,
  ),
);
console.log("\nAccounts:");
for (const a of ix.accounts || []) {
  console.log(` - ${a.name}  isMut=${!!a.isMut}  isSigner=${!!a.isSigner}`);
}
