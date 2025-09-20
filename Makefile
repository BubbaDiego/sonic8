.PHONY: install dev-api dev-web openapi spec-validate spec-ci

install:
	python -m pip install -r requirements.txt
	cd frontend && npm install

dev-api:
	uvicorn backend.sonic_backend_app:app --reload

dev-web:
	cd frontend && npm run dev

openapi:
	python backend/scripts/export_openapi.py

spec-validate:
	python backend/scripts/spec_validate_checks.py

spec-ci: spec-validate

.PHONY: ui-validate
ui-validate:
	python backend/scripts/validate_ui_manifest.py

.PHONY: ui-sweep ui-snap
ui-sweep:
	python backend/scripts/ui_sweeper.py
ui-snap:
	UI_BASE_URL=http://127.0.0.1:5173 python backend/scripts/ui_snapshots.py
.PHONY: ui-doc
ui-doc:
	python backend/scripts/build_ui_components_doc.py
.PHONY: spec-all
spec-all:
	python backend/scripts/validate_all_specs.py

.PHONY: spec-daily
spec-daily:
	python backend/scripts/spec_api_mapper.py
	python backend/scripts/spec_schema_sampler.py
	python backend/scripts/ui_sweeper.py
	python backend/scripts/export_openapi.py || true
	python backend/scripts/build_ui_components_doc.py
	python backend/scripts/validate_all_specs.py

