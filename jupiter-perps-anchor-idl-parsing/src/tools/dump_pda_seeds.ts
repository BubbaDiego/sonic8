// Print PDA seed specs for key accounts from the local IDL.
// Run:
//   TS_NODE_PROJECT=jupiter-perps-anchor-idl-parsing/tsconfig.json \
//     node --import "data:text/javascript,import { register } from 'node:module'; import { pathToFileURL } from 'node:url'; register('ts-node/esm', pathToFileURL('./'));" --experimental-specifier-resolution=node \
//     jupiter-perps-anchor-idl-parsing/src/tools/dump_pda_seeds.ts

import { IDL } from "../idl/jupiter-perpetuals-idl.js";

function find(name: string) {
  const acc = (IDL as any).accounts?.find(
    (a: any) => a?.name?.toLowerCase?.() === name.toLowerCase()
  );
  if (!acc) return null;
  return {
    name: acc.name,
    pda: acc.pda ?? null,
    // show instruction account metas that reference this, for sanity
    usedBy: (IDL as any).instructions
      ?.filter((ix: any) => ix?.accounts?.some((m: any) => m?.name === name))
      ?.map((ix: any) => ix.name),
  };
}

function show(name: string) {
  const x = find(name);
  console.log("\n=== ", name, " ===");
  if (!x) {
    console.log("(not found in IDL.accounts)");
  } else {
    console.log(JSON.stringify(x, null, 2));
  }
}

console.log("IDL has", (IDL as any).accounts?.length ?? 0, "accounts");
show("position");
show("positionRequest");
show("pool");
show("custody");
