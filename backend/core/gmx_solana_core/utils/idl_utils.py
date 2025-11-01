def ensure_idl_has_program(idl: dict, name: str) -> bool:
    # Phase S-2: inspect IDL contents for program names
    return name in (idl.get("name") or "")
