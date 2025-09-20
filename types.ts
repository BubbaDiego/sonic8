export type Side = "long" | "short";

export type RemainingAccount = {
  pubkey: string;
  isSigner: boolean;
  isWritable: boolean;
};
