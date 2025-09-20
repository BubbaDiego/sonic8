## Summary
<!-- What changed and why? -->

## Daily Maintenance Checklist (run before marking ready)
- [ ] `python backend/scripts/spec_api_mapper.py` (map new API routes)
- [ ] `python backend/scripts/spec_schema_sampler.py` (draft schemas for unmapped routes)
- [ ] `python backend/scripts/ui_sweeper.py` (refresh UI routes/components/props)
- [ ] `python backend/scripts/export_openapi.py` (regenerate OpenAPI)
- [ ] `python backend/scripts/build_ui_components_doc.py` (refresh UI components doc)
- [ ] `python backend/scripts/validate_all_specs.py` (all green: backend + UI)
- [ ] (Optional) `UI_BASE_URL=http://127.0.0.1:5173 python backend/scripts/ui_snapshots.py` (update screenshots)

## Screenshots / Visuals (if UI changed)
<!-- Drop images or describe visual changes -->

## Risks / Rollback
<!-- Any risk + how to revert safely -->
