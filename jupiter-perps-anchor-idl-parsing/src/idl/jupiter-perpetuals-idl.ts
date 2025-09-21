import { createRequire } from "module";

const require = createRequire(import.meta.url);

export const IDL = require("../../jupiter-perpetuals-idl-json.json");
