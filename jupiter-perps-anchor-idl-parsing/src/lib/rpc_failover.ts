import { Connection, Commitment } from "@solana/web3.js";

export type RpcPoolOpts = {
  commitment?: Commitment;
  perEndpointMaxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
};

export class RpcPool {
  private endpoints: string[];
  private i = 0;
  private opts: Required<RpcPoolOpts>;

  constructor(primary: string, fallbacksCsv?: string, opts?: RpcPoolOpts) {
    const fb = (fallbacksCsv ?? process.env.SONIC_SOLANA_RPC_FALLBACKS ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const all = [primary, ...fb];
    const envPrimary = process.env.SONIC_SOLANA_RPC_PRIMARY?.trim();
    this.endpoints = envPrimary ? [envPrimary, ...all.filter((e) => e !== envPrimary)] : all;

    this.opts = {
      commitment: opts?.commitment ?? "confirmed",
      perEndpointMaxRetries: Math.max(
        1,
        opts?.perEndpointMaxRetries ?? parseInt(process.env.SONIC_SOLANA_RPC_MAX_RETRIES ?? "4", 10),
      ),
      baseDelayMs: opts?.baseDelayMs ?? 500,
      maxDelayMs: opts?.maxDelayMs ?? 12000,
    };
  }

  currentEndpoint(): string {
    return this.endpoints[this.i % this.endpoints.length];
  }

  private nextEndpoint() {
    this.i = (this.i + 1) % this.endpoints.length;
  }

  private static jitter(ms: number) {
    const j = Math.floor(ms * 0.25);
    return ms + Math.floor(Math.random() * j);
  }

  private static sleep(ms: number) {
    return new Promise((res) => setTimeout(res, ms));
  }

  /** Heuristic check for 429 / rate-limit / overload style errors */
  static isRateLimitish(e: any): boolean {
    const s = (e?.message ?? e?.toString?.() ?? "").toLowerCase();
    return (
      s.includes("429") ||
      s.includes("too many requests") ||
      s.includes("rate limit") ||
      s.includes("overloaded") ||
      s.includes("request limit") ||
      s.includes("service unavailable") ||
      s.includes("http 429")
    );
  }

  /** Run fn with retries + endpoint rotation on rate-limitish errors. */
  async runWithFailover<T>(fnFactory: (conn: Connection) => Promise<T>, label: string): Promise<T> {
    let attempt = 0;
    let perEndpointAttempt = 0;

    for (let rotations = 0; rotations < this.endpoints.length * 3; rotations++) {
      const endpoint = this.currentEndpoint();
      const conn = new Connection(endpoint, this.opts.commitment);

      perEndpointAttempt = 0;

      while (perEndpointAttempt < this.opts.perEndpointMaxRetries) {
        attempt++;
        perEndpointAttempt++;

        try {
          return await fnFactory(conn);
        } catch (e: any) {
          const isRate = RpcPool.isRateLimitish(e);
          const delayBase = Math.min(
            this.opts.maxDelayMs,
            this.opts.baseDelayMs * Math.pow(2, Math.min(perEndpointAttempt - 1, 6)),
          );
          const delay = RpcPool.jitter(delayBase);

          if (isRate) {
            console.warn(
              `⚠️ RPC 429/limit on "${label}" (endpoint=${endpoint}) attempt ${perEndpointAttempt}/${this.opts.perEndpointMaxRetries}. Backoff ${delay}ms…`,
            );
            await RpcPool.sleep(delay);
            continue;
          }

          // Non-rate error: bubble up immediately.
          throw e;
        }
      }

      const old = endpoint;
      this.nextEndpoint();
      const next = this.currentEndpoint();
      console.warn(`🔁 Rotating RPC endpoint: ${old} → ${next}`);
    }

    throw new Error(`RPC failover exhausted for "${label}".`);
  }
}
