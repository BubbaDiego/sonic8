import os
import subprocess


def yesno(prompt: str, default: bool = False) -> bool:
    choice = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not choice:
        return default
    return choice.startswith('y')


def menu_balances():
    use_signer = yesno("Use current signer from .env?", True)
    scan_all = yesno("Scan all SPLs (show any non-zero tokens)?", True)
    if use_signer:
        pub = os.getenv("PUBKEY")
        if not pub:
            print("❌ No signer configured. Set PUBKEY environment variable")
            return
        args = ["--pubkey", pub]
        if scan_all:
            args.append("--all")
        rc = subprocess.call(["python", "wallet_balances.py", *args])
    else:
        pk = input("Enter address (base58): ").strip()
        if not pk:
            print("❌ address required")
            return
        args = ["--pubkey", pk]
        if scan_all:
            args.append("--all")
        rc = subprocess.call(["python", "wallet_balances.py", *args])
    if rc != 0:
        print(f"❌ balances exited with {rc}")


if __name__ == "__main__":
    menu_balances()
