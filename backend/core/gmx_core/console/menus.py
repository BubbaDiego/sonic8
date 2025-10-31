def header(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def kv(key: str, value: str) -> None:
    print(f"{key:>18}: {value}")
