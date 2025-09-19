.PHONY: install dev-api dev-web openapi spec-validate

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
	python backend/scripts/spec_validate.py
