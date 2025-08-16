# ---- Sonic Spec Bundle ----
.PHONY: spec-sync spec-validate openapi schemas

spec-sync:
	python scripts/spec_sync.py

spec-validate:
	python scripts/spec_validate.py

openapi:
	python api/generate_openapi.py

schemas:
	python scripts/spec_sync.py --schemas-only
