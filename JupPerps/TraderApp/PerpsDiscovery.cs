using System;
using System.Threading.Tasks;
using Solnet.Rpc;
using Solnet.Rpc.Types;
using Solnet.Wallet;

namespace TraderApp
{
    /// <summary>
    /// Perps + Custody discovery without MemCmp or discriminator constants.
    /// Strategy:
    ///  - Perpetuals: env → PDALookup(pool) → seed("perpetuals") → owner+data check
    ///  - Custody:    env → PDALookup(mint) → owner+data check
    /// The only validation enforced here is owner==PERPS_PROGRAM_ID and data non-empty.
    /// </summary>
    internal static class PerpsDiscovery
    {
        /// <summary>
        /// Returns a PDALookup-derived Perpetuals PDA from a pool (or default on failure).
        /// Provided because Program.cs calls this by name.
        /// </summary>
        public static PublicKey TryFindPerpetualsBySdkHint(PublicKey pool)
        {
            try { return Solnet.JupiterPerps.PDALookup.FindPerpetualsPDA(pool); }
            catch { return default; }
        }

        /// <summary>
        /// Validate a candidate Perpetuals account: owner is PERPS program and data is non-empty.
        /// </summary>
        public static bool TryGetValidPerpetuals(IRpcClient rpc, PublicKey candidate, out PublicKey valid)
        {
            valid = default;
            try
            {
                if (candidate.Key == null) return false;
                var info = rpc.GetAccountInfoAsync(candidate.Key, Commitment.Confirmed).Result;
                if (!info.WasSuccessful || info.Result?.Value == null) return false;
                if (info.Result.Value.Owner != Program.PERPS_PROGRAM_ID.Key) return false;
                var b64 = info.Result.Value.Data?[0];
                if (string.IsNullOrEmpty(b64)) return false;
                valid = candidate;
                return true;
            }
            catch { return false; }
        }

        /// <summary>
        /// Synchronous-compatible "Async" variant with the same semantics.
        /// </summary>
        public static bool TryGetValidPerpetualsAsync(IRpcClient rpc, PublicKey candidate, out PublicKey valid)
            => TryGetValidPerpetuals(rpc, candidate, out valid);

        /// <summary>
        /// Overload used by some Program.cs paths that only need a boolean check.
        /// </summary>
        public static bool TryGetValidPerpetualsAsync(IRpcClient rpc, PublicKey candidate)
            => TryGetValidPerpetuals(rpc, candidate, out _);

        /// <summary>
        /// Resolve Perpetuals using the robust path (env → PDALookup(pool) → seed("perpetuals")).
        /// </summary>
        public static PublicKey ResolvePerpetuals(IRpcClient rpc, PublicKey pool)
        {
            // env
            var envPerp = Environment.GetEnvironmentVariable("JUP_PERPETUALS");
            if (!string.IsNullOrWhiteSpace(envPerp))
            {
                var pk = new PublicKey(envPerp.Trim());
                if (TryGetValidPerpetuals(rpc, pk, out var ok))
                {
                    Logging.Info($"✅ Perpetuals via env: {ok}");
                    return ok;
                }
                Logging.Warn("⚠️ Perpetuals env value invalid (owner/data).");
            }

            // PDALookup by pool
            try
            {
                var pda = Solnet.JupiterPerps.PDALookup.FindPerpetualsPDA(pool);
                if (TryGetValidPerpetuals(rpc, pda, out var ok2))
                {
                    Logging.Info($"✅ Perpetuals via SDK hint: {ok2}");
                    return ok2;
                }
                Logging.Warn("⚠️ SDK-hinted Perpetuals invalid (owner/data).");
            }
            catch { /* continue */ }

            // seed("perpetuals")
            try
            {
                var seed = PdaUtils.DerivePda("perpetuals", Program.PERPS_PROGRAM_ID);
                if (TryGetValidPerpetuals(rpc, seed, out var ok3))
                {
                    Logging.Info($"✅ Perpetuals via seed('perpetuals'): {ok3}");
                    return ok3;
                }
            }
            catch { }

            Logging.Warn("⚠️ Perpetuals not found via env/SDK/seed.");
            return default;
        }

        /// <summary>
        /// Program.cs calls a scan variant; provide a compatible method that delegates to our robust resolver with the known pool.
        /// </summary>
        public static PublicKey ResolvePerpetualsWithScan(IRpcClient rpc)
            => ResolvePerpetuals(rpc, Program.JLP_POOL);

        /// <summary>
        /// Resolve custody for a given mint using env → PDALookup + owner/data checks.
        /// </summary>
        public static async Task<PublicKey> ResolveCustodyWithDebug(string label, IRpcClient rpc, PublicKey mint)
        {
            var envName = label.Contains("Collateral", StringComparison.OrdinalIgnoreCase) ? "JUP_COLLATERAL_CUSTODY" : "JUP_CUSTODY";
            var fromEnv = Environment.GetEnvironmentVariable(envName);
            if (!string.IsNullOrWhiteSpace(fromEnv))
            {
                var envPk = new PublicKey(fromEnv.Trim());
                Logging.Info($"ℹ️ {label}: using {envName}={envPk}");
                if (await ValidateOwnerDataAsync(rpc, envPk, label)) return envPk;
                Logging.Warn($"⚠️ {label}: env {envName} invalid (owner/data).");
            }

            // PDALookup
            try
            {
                var pda = Solnet.JupiterPerps.PDALookup.FindCustodyPDA(mint);
                if (await ValidateOwnerDataAsync(rpc, pda, label))
                {
                    Logging.Info($"✅ {label}: PDALookup → {pda} (mint={mint})");
                    return pda;
                }
                Logging.Warn($"⚠️ {label}: PDALookup candidate invalid (owner/data).");
            }
            catch { }

            Logging.Warn($"⚠️ {label}: Unable to resolve a valid Custody for mint={mint}. Set {envName}=<pubkey> and re-run.");
            return default;
        }

        /// <summary>
        /// Owner + data check only (no discriminator dependency).
        /// </summary>
        private static async Task<bool> ValidateOwnerDataAsync(IRpcClient rpc, PublicKey pk, string label)
        {
            try
            {
                var info = await rpc.GetAccountInfoAsync(pk.Key, Commitment.Confirmed);
                if (!info.WasSuccessful || info.Result?.Value == null) { Logging.Warn($"⚠️ {label}: account not found: {pk}"); return false; }
                if (info.Result.Value.Owner != Program.PERPS_PROGRAM_ID.Key) { Logging.Warn($"⚠️ {label}: owner mismatch; expected {Program.PERPS_PROGRAM_ID.Key}, got {info.Result.Value.Owner}"); return false; }
                var b64 = info.Result.Value.Data?[0]; if (string.IsNullOrEmpty(b64)) { Logging.Warn($"⚠️ {label}: empty data"); return false; }
                return true;
            }
            catch (Exception ex)
            {
                Logging.Warn($"⚠️ {label}: validation exception: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Kept for compatibility with earlier code paths that wanted "anchor-style" validation.
        /// </summary>
        public static async Task<bool> ValidateAnchorAccount(IRpcClient rpc, PublicKey pk, string accountName, string label)
            => await ValidateOwnerDataAsync(rpc, pk, label);
    }
}

