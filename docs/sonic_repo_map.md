# Sonic Repository Map

This file lists every folder and file in the repository (excluding directories like `node_modules`, `.git`, `.idea`, `__pycache__`, and `.venv`).

```txt
.
├── .github
│   └── workflows
│       └── ci.yml
├── .gitignore
├── README.md
├── api
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── alert.py
│   │   ├── order.py
│   │   ├── position.py
│   │   ├── signal.py
│   │   └── strategy.py
│   └── openapi.yaml
├── backend
│   ├── .cache
│   │   └── wallet_registry.json
│   ├── __init__.py
│   ├── config
│   │   ├── __init__.py
│   │   ├── active_traders.json
│   │   ├── alert_thresholds.json
│   │   ├── comm_config.json
│   │   ├── config_loader.py
│   │   ├── perpetual_tokens.json
│   │   ├── sample_alerts.json
│   │   ├── sonic_config.json
│   │   ├── sonic_sauce.json
│   │   ├── theme_config.json
│   │   └── timer_config.json
│   ├── controllers
│   │   ├── __init__.py
│   │   ├── cyclone_controller.py
│   │   ├── logic.py
│   │   └── monitor_controller.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── alert_core
│   │   │   ├── __init__.py
│   │   │   ├── alert_controller.py
│   │   │   ├── alert_core_spec.md
│   │   │   ├── config
│   │   │   │   └── loader.py
│   │   │   ├── infrastructure
│   │   │   │   ├── notifiers
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── router.py
│   │   │   │   │   ├── sms.py
│   │   │   │   │   └── windows_toast.py
│   │   │   │   └── stores.py
│   │   │   ├── services
│   │   │   │   ├── enrichment.py
│   │   │   │   ├── evaluation.py
│   │   │   │   └── orchestration.py
│   │   │   ├── threshold_service.py
│   │   │   └── utils.py
│   │   ├── auto_core
│   │   │   ├── __init__.py
│   │   │   ├── auto_core.py
│   │   │   ├── playwright_helper.py
│   │   │   ├── requests
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── web_browser.py
│   │   │   └── steps
│   │   │       ├── connect_jupiter_solflare.py
│   │   │       ├── select_asset.py
│   │   │       ├── solflare_unlock_only.py
│   │   │       └── switch_wallet_from_signer.py
│   │   ├── calc_core
│   │   │   ├── __init__.py
│   │   │   ├── calc_services.py
│   │   │   ├── calculation_core.py
│   │   │   ├── calculation_module_spec.md
│   │   │   └── calculation_services.py
│   │   ├── core_constants.py
│   │   ├── cyclone_core
│   │   │   ├── __init__.py
│   │   │   ├── cyclone_alert_service.py
│   │   │   ├── cyclone_bp.py
│   │   │   ├── cyclone_core_spec.md
│   │   │   ├── cyclone_engine.py
│   │   │   ├── cyclone_hedge_service.py
│   │   │   ├── cyclone_maintenance_service.py
│   │   │   ├── cyclone_portfolio_service.py
│   │   │   ├── cyclone_position_service.py
│   │   │   ├── cyclone_report_generator.py
│   │   │   ├── cyclone_wallet_service.py
│   │   │   ├── test_cyclone_step_create_position_alerts.py
│   │   │   └── test_cyclone_step_enrich_positions.py
│   │   ├── fun_core
│   │   │   ├── __init__.py
│   │   │   ├── fun_router.py
│   │   │   ├── models.py
│   │   │   ├── monitor.py
│   │   │   ├── registry.py
│   │   │   └── services
│   │   │       ├── base.py
│   │   │       ├── joke_service.py
│   │   │       ├── quote_service.py
│   │   │       └── trivia_service.py
│   │   ├── hedge_core
│   │   │   ├── __init__.py
│   │   │   ├── auto_hedge_wizard.py
│   │   │   ├── hedge_calc_services.py
│   │   │   ├── hedge_calc_services_spec.md
│   │   │   ├── hedge_core.py
│   │   │   ├── hedge_core_module_spec.md
│   │   │   ├── hedge_services.py
│   │   │   └── hedge_wizard_bp.py
│   │   ├── logging.py
│   │   ├── market_core
│   │   │   ├── daily_swing_service.py
│   │   │   ├── market_core_spec.md
│   │   │   └── price_sync_service.py
│   │   ├── monitor_core
│   │   │   ├── __init__.py
│   │   │   ├── base_monitor.py
│   │   │   ├── latency_monitor.py
│   │   │   ├── ledger_service.py
│   │   │   ├── liquidation_monitor.py
│   │   │   ├── market_monitor.py
│   │   │   ├── monitor_api.py
│   │   │   ├── monitor_console.py
│   │   │   ├── monitor_core.py
│   │   │   ├── monitor_core_spec.md
│   │   │   ├── monitor_registry.py
│   │   │   ├── monitor_service.py
│   │   │   ├── monitor_utils.py
│   │   │   ├── operations_monitor.py
│   │   │   ├── position_monitor.py
│   │   │   ├── price_monitor.py
│   │   │   ├── profit_monitor.py
│   │   │   ├── profit_monitor_spec.md
│   │   │   ├── risk_monitor.py
│   │   │   ├── risk_monitor_spec.md
│   │   │   ├── sonic_events.py
│   │   │   ├── sonic_monitor.py
│   │   │   ├── test_monitor_core.py
│   │   │   ├── test_twilio.py
│   │   │   ├── twilio_monitor.py
│   │   │   └── xcom_monitor.py
│   │   ├── oracle_core
│   │   │   ├── __init__.py
│   │   │   ├── alerts_topic_handler.py
│   │   │   ├── oracle_core.py
│   │   │   ├── oracle_core_spec.md
│   │   │   ├── oracle_data_service.py
│   │   │   ├── oracle_services.py
│   │   │   ├── persona_manager.py
│   │   │   ├── portfolio_topic_handler.py
│   │   │   ├── positions_topic_handler.py
│   │   │   ├── prices_topic_handler.py
│   │   │   ├── strategies
│   │   │   │   ├── cautious.json
│   │   │   │   ├── degen.json
│   │   │   │   ├── dynamic_hedging.json
│   │   │   │   ├── heat_control.json
│   │   │   │   ├── none.json
│   │   │   │   ├── profit_management.json
│   │   │   │   ├── safe.json
│   │   │   │   └── test.json
│   │   │   ├── strategy_manager.py
│   │   │   └── system_topic_handler.py
│   │   ├── positions_core
│   │   │   ├── __init__.py
│   │   │   ├── hedge_manager.py
│   │   │   ├── position_core.py
│   │   │   ├── position_core_detailed_spec.md
│   │   │   ├── position_core_service.py
│   │   │   ├── position_enrichment_service.py
│   │   │   ├── position_module_spec.md
│   │   │   ├── position_store.py
│   │   │   └── position_sync_service.py
│   │   ├── trader_core
│   │   │   ├── __init__.py
│   │   │   ├── mood_engine.py
│   │   │   ├── persona_avatars.py
│   │   │   ├── personas
│   │   │   │   ├── Angie.json
│   │   │   │   ├── C3P0.json
│   │   │   │   ├── Chewie.json
│   │   │   │   ├── Connie.json
│   │   │   │   ├── Jabba.json
│   │   │   │   ├── Lando.json
│   │   │   │   ├── Leia.json
│   │   │   │   ├── Luke.json
│   │   │   │   ├── Nina.json
│   │   │   │   ├── Palpatine.json
│   │   │   │   ├── R2.json
│   │   │   │   ├── Selena.json
│   │   │   │   ├── Vader.json
│   │   │   │   ├── Wizard.json
│   │   │   │   ├── Yoda.json
│   │   │   │   └── risk_averse.json
│   │   │   ├── trader_bp.py
│   │   │   ├── trader_core.py
│   │   │   ├── trader_core_spec.md
│   │   │   ├── trader_factory_service.py
│   │   │   ├── trader_loader.py
│   │   │   ├── trader_store.py
│   │   │   └── trader_update_service.py
│   │   ├── wallet_core
│   │   │   ├── __init__.py
│   │   │   ├── encryption.py
│   │   │   ├── jupiter_api_spec.md
│   │   │   ├── test_wallets
│   │   │   │   └── star_wars_wallets.json
│   │   │   ├── wallet_controller.py
│   │   │   ├── wallet_core.py
│   │   │   ├── wallet_core_spec.md
│   │   │   ├── wallet_repository.py
│   │   │   ├── wallet_schema.py
│   │   │   └── wallet_service.py
│   │   └── xcom_core
│   │       ├── __init__.py
│   │       ├── alexa_service.py
│   │       ├── check_twilio_heartbeat_service.py
│   │       ├── email_service.py
│   │       ├── notification_service.py
│   │       ├── sms_service.py
│   │       ├── sound_service.py
│   │       ├── tts_service.py
│   │       ├── voice_service.py
│   │       ├── xcom_config_service.py
│   │       ├── xcom_core.py
│   │       ├── xcom_core_spec.md
│   │       └── xcom_status_service.py
│   ├── data
│   │   ├── __init__.py
│   │   ├── data_locker.py
│   │   ├── database.py
│   │   ├── dl_alerts.py
│   │   ├── dl_hedges.py
│   │   ├── dl_modifiers.py
│   │   ├── dl_monitor_ledger.py
│   │   ├── dl_notification_manager.py
│   │   ├── dl_portfolio.py
│   │   ├── dl_positions.py
│   │   ├── dl_prices.py
│   │   ├── dl_session.py
│   │   ├── dl_system_data.py
│   │   ├── dl_thresholds.py
│   │   ├── dl_traders.py
│   │   ├── dl_wallets.py
│   │   ├── learning_database
│   │   │   ├── __init__.py
│   │   │   ├── learning_bp.py
│   │   │   ├── learning_data_locker.py
│   │   │   ├── learning_db_app.py
│   │   │   ├── learning_event_logger.py
│   │   │   ├── learning_system_spec.md
│   │   │   └── scripts
│   │   │       ├── __init__.py
│   │   │       └── verify_all_tables_exist.py
│   │   ├── locker_factory.py
│   │   ├── models_core.py
│   │   └── reset_database.py
│   ├── deps.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   ├── alert_thresholds.py
│   │   ├── hedge.py
│   │   ├── monitor_status.py
│   │   ├── portfolio.py
│   │   ├── position.py
│   │   ├── session.py
│   │   ├── system_data.py
│   │   ├── trader.py
│   │   ├── wallet.py
│   │   └── xcom_models.py
│   ├── mother.db
│   ├── perps
│   │   ├── __init__.py
│   │   ├── anchor_raw.py
│   │   ├── constants.py
│   │   ├── idl.py
│   │   ├── pdas.py
│   │   ├── rpc.py
│   │   ├── seeds_fix.py
│   │   └── sim_send.py
│   ├── routers
│   │   ├── __init__.py
│   │   └── jupiter.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── alert_thresholds_api.py
│   │   ├── auto_core_api.py
│   │   ├── cyclone_api.py
│   │   ├── db_admin_api.py
│   │   ├── fun_api.py
│   │   ├── jupiter_api.py
│   │   ├── jupiter_perps_api.py
│   │   ├── liquidation_distance_api.py
│   │   ├── market_api.py
│   │   ├── monitor_api_adapter.py
│   │   ├── monitor_settings_api.py
│   │   ├── monitor_status_api.py
│   │   ├── notification_api.py
│   │   ├── portfolio_api.py
│   │   ├── positions_api.py
│   │   ├── prices_api.py
│   │   ├── session_api.py
│   │   ├── solana_api.py
│   │   ├── traders_api.py
│   │   ├── wallet_api.py
│   │   ├── wallet_verify_api.py
│   │   └── xcom_api.py
│   ├── scripts
│   │   ├── __init__.py
│   │   ├── api_breakpoint_test.py
│   │   ├── backfill_price_history.py
│   │   ├── create_virtual_env.py
│   │   ├── crypto utils
│   │   │   ├── balances_bulk.py
│   │   │   ├── crypto_console.py
│   │   │   ├── derive_keypair.py
│   │   │   ├── dump_token_accounts.py
│   │   │   ├── find_index.py
│   │   │   ├── helius_ws_watch.py
│   │   │   ├── import_secret_to_base64.py
│   │   │   ├── jup_swap_to_sol.py
│   │   │   ├── match_indices.py
│   │   │   └── wallet_balances.py
│   │   ├── diagnose_market_monitor.py
│   │   ├── env_load_test.py
│   │   ├── fetch_perps_idl.py
│   │   ├── ifttt_alex_verify.py
│   │   ├── initialize_database.py
│   │   ├── insert_star_wars_traders.py
│   │   ├── insert_star_wars_wallets.py
│   │   ├── insert_wallets.py
│   │   ├── int_learning_db.py
│   │   ├── new_tree_protocol.py
│   │   ├── openai_test.py
│   │   ├── openapi_to_quickdocs.py
│   │   ├── perps_open_long.py
│   │   ├── populate_learning_db.py
│   │   ├── recover_database.py
│   │   ├── run_alexa_notify.py
│   │   ├── run_zira_tts.py
│   │   ├── scan_imports.py
│   │   ├── seed_alert_thresholds.py
│   │   ├── seed_portfolio_history.py
│   │   ├── send_sms_demo.py
│   │   ├── setup_test_env.py
│   │   ├── spec_audit.py
│   │   ├── test.py
│   │   ├── twilio_auth_test.py
│   │   ├── twilio_run.py
│   │   ├── twilio_test.py
│   │   ├── twilio_verify.py
│   │   ├── update_spec.py
│   │   ├── verify_all_tables_exist.py
│   │   ├── verify_position_schema.py
│   │   ├── verify_profit_alert.py
│   │   └── verify_risk_alert.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── database_service.py
│   │   ├── external_api_service.py
│   │   ├── jupiter_perps.py
│   │   ├── jupiter_swap.py
│   │   ├── jupiter_trigger.py
│   │   ├── perps
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── idl
│   │   │   │   └── jupiter_perpetuals.json
│   │   │   ├── markets.py
│   │   │   └── positions.py
│   │   ├── position_service.py
│   │   ├── profit_watcher.py
│   │   ├── signer_loader.py
│   │   ├── txlog.py
│   │   ├── xcom_service.py
│   │   └── xcom_status_service.py
│   ├── sitecustomize.py
│   ├── sonic_backend_app.py
│   └── utils
│       ├── CONSOLE_LOGGER_SPEC.md
│       ├── __init__.py
│       ├── alert_helpers.py
│       ├── clear_caches.py
│       ├── console_logger.py
│       ├── console_title.py
│       ├── db_retry.py
│       ├── env_utils.py
│       ├── fuzzy_wuzzy.py
│       ├── hedge_colors.py
│       ├── json_manager.py
│       ├── net_utils.py
│       ├── path_audit.py
│       ├── path_auto_fixer.py
│       ├── rich_logger.py
│       ├── route_decorators.py
│       ├── schema_validation_service.py
│       ├── startup_checker.py
│       ├── startup_service.py
│       ├── template_filters.py
│       ├── time_utils.py
│       ├── travel_percent_logger.py
│       └── update_ledger.py
├── balances_bulk.py
├── core
│   └── models
│       ├── __init__.py
│       ├── account.py
│       ├── alert.py
│       ├── order.py
│       ├── position.py
│       ├── signal.py
│       └── strategy.py
├── crypto_console.py
├── data
│   └── learning_database.db
├── docs
│   ├── alert_system__spec.md
│   ├── alert_thresholds_api.md
│   ├── backend_api_spec.md
│   ├── berry_react_guide.md
│   ├── dev_setup.md
│   ├── form_ui_description.md
│   ├── frontend_api_spec.md
│   ├── frontend_file_description.md
│   ├── frontend_repo_map.md
│   ├── fun_core_integration.md
│   ├── fun_core_spec.md
│   ├── price_api_24hr.md
│   ├── repo_map.md
│   ├── research
│   │   ├── Free Crypto APIs for 24h High_Low Price Data.pdf
│   │   └── blast_radius_numbers.md
│   ├── schemas
│   │   ├── account.json
│   │   ├── alert.json
│   │   ├── liquidation_alert_request.json
│   │   ├── order.json
│   │   ├── order_create.json
│   │   ├── position.json
│   │   ├── position_adjust_request.json
│   │   ├── signal.json
│   │   └── strategy.json
│   ├── sonic_design_spec.md
│   ├── sonic_react_grid_spec.md
│   ├── sonic_repo_map_content.txt
│   ├── spec
│   │   ├── _spec_audit_report.txt
│   │   ├── api_index.md
│   │   ├── domain_glossary.md
│   │   ├── master.md
│   │   ├── open_questions.md
│   │   ├── ui_contracts.md
│   │   └── workflows.md
│   ├── teaching_pack
│   │   └── 04_api_quick.md
│   ├── trader_shop_frontend.md
│   └── ui_theme_spec.md
├── dump_token_accounts.py
├── frontend
│   ├── .env
│   ├── .env.qa
│   ├── .gitignore
│   ├── .prettierrc
│   ├── .yarn
│   │   └── install-state.gz
│   ├── .yarnrc.yml
│   ├── __tests__
│   │   ├── AlertThresholdInteractions.test.jsx
│   │   ├── AlertThresholdPage.test.jsx
│   │   ├── DonutCountdown.test.jsx
│   │   ├── MonitorManager.test.jsx
│   │   ├── PositionsTableCard.test.jsx
│   │   └── ThresholdTable.test.jsx
│   ├── babel.config.js
│   ├── eslint.config.mjs
│   ├── favicon.svg
│   ├── index.html
│   ├── jest.config.js
│   ├── jsconfig.json
│   ├── jsconfig.node.json
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.cjs
│   ├── public
│   │   └── abstract_mural.png
│   ├── src
│   │   ├── App.jsx
│   │   ├── api
│   │   │   ├── alertThresholds.js
│   │   │   ├── cyclone.js
│   │   │   ├── jupiter.js
│   │   │   ├── jupiter.perps.js
│   │   │   ├── menu.js
│   │   │   ├── monitorStatus.js
│   │   │   ├── portfolio.js
│   │   │   ├── positions.js
│   │   │   ├── prices.js
│   │   │   ├── session.js
│   │   │   ├── sonicMonitor.js
│   │   │   ├── thresholdApi.js
│   │   │   ├── traders.js
│   │   │   ├── wallets.js
│   │   │   └── xcom.js
│   │   ├── assets
│   │   │   ├── images
│   │   │   │   ├── auth
│   │   │   │   │   ├── auth-blue-card.svg
│   │   │   │   │   ├── auth-forgot-pass-multi-card.svg
│   │   │   │   │   ├── auth-mail-blue-card.svg
│   │   │   │   │   ├── auth-pattern-dark.svg
│   │   │   │   │   ├── auth-pattern.svg
│   │   │   │   │   ├── auth-purple-card.svg
│   │   │   │   │   ├── auth-reset-error-card.svg
│   │   │   │   │   ├── auth-reset-purple-card.svg
│   │   │   │   │   ├── auth-signup-blue-card.svg
│   │   │   │   │   ├── auth-signup-white-card.svg
│   │   │   │   │   ├── img-a2-checkmail.svg
│   │   │   │   │   ├── img-a2-codevarify.svg
│   │   │   │   │   ├── img-a2-forgotpass.svg
│   │   │   │   │   ├── img-a2-grid-dark.svg
│   │   │   │   │   ├── img-a2-grid.svg
│   │   │   │   │   ├── img-a2-login.svg
│   │   │   │   │   ├── img-a2-resetpass.svg
│   │   │   │   │   └── img-a2-signup.svg
│   │   │   │   ├── blog
│   │   │   │   │   ├── blog-1.png
│   │   │   │   │   ├── blog-2.png
│   │   │   │   │   ├── blog-3.png
│   │   │   │   │   ├── blog-4.png
│   │   │   │   │   ├── blog-5.png
│   │   │   │   │   ├── blog-6.png
│   │   │   │   │   ├── blog-7.png
│   │   │   │   │   ├── blog-8.png
│   │   │   │   │   ├── library-1.png
│   │   │   │   │   ├── library-2.png
│   │   │   │   │   ├── library-3.png
│   │   │   │   │   └── post-banner.png
│   │   │   │   ├── customization
│   │   │   │   │   ├── big.svg
│   │   │   │   │   ├── horizontal.svg
│   │   │   │   │   ├── ltr.svg
│   │   │   │   │   ├── max.svg
│   │   │   │   │   ├── mini.svg
│   │   │   │   │   ├── rtl.svg
│   │   │   │   │   ├── small.svg
│   │   │   │   │   └── vertical.svg
│   │   │   │   ├── icons
│   │   │   │   │   ├── auth0.svg
│   │   │   │   │   ├── aws.svg
│   │   │   │   │   ├── earning.svg
│   │   │   │   │   ├── facebook.svg
│   │   │   │   │   ├── firebase.svg
│   │   │   │   │   ├── google.svg
│   │   │   │   │   ├── jwt.svg
│   │   │   │   │   ├── linkedin.svg
│   │   │   │   │   ├── supabase.svg
│   │   │   │   │   └── twitter.svg
│   │   │   │   ├── landing
│   │   │   │   │   └── pre-apps
│   │   │   │   │       ├── slider-dark-1.png
│   │   │   │   │       ├── slider-dark-2.png
│   │   │   │   │       ├── slider-dark-3.png
│   │   │   │   │       ├── slider-dark-4.png
│   │   │   │   │       ├── slider-dark-5.png
│   │   │   │   │       ├── slider-dark-6.png
│   │   │   │   │       ├── slider-dark-7.png
│   │   │   │   │       ├── slider-dark-8.png
│   │   │   │   │       ├── slider-light-1.png
│   │   │   │   │       ├── slider-light-2.png
│   │   │   │   │       ├── slider-light-3.png
│   │   │   │   │       ├── slider-light-4.png
│   │   │   │   │       ├── slider-light-5.png
│   │   │   │   │       ├── slider-light-6.png
│   │   │   │   │       ├── slider-light-7.png
│   │   │   │   │       └── slider-light-8.png
│   │   │   │   ├── logo-dark.svg
│   │   │   │   ├── logo.svg
│   │   │   │   ├── maintenance
│   │   │   │   │   ├── 500-error.svg
│   │   │   │   │   ├── empty-dark.svg
│   │   │   │   │   ├── empty.svg
│   │   │   │   │   ├── img-bg-grid-dark.svg
│   │   │   │   │   ├── img-bg-grid.svg
│   │   │   │   │   ├── img-bg-parts.svg
│   │   │   │   │   ├── img-build.svg
│   │   │   │   │   ├── img-ct-dark-logo.png
│   │   │   │   │   ├── img-ct-light-logo.png
│   │   │   │   │   ├── img-error-bg-dark.svg
│   │   │   │   │   ├── img-error-bg.svg
│   │   │   │   │   ├── img-error-blue.svg
│   │   │   │   │   ├── img-error-purple.svg
│   │   │   │   │   ├── img-error-text.svg
│   │   │   │   │   ├── img-soon-2.svg
│   │   │   │   │   ├── img-soon-3.svg
│   │   │   │   │   ├── img-soon-4.svg
│   │   │   │   │   ├── img-soon-5.svg
│   │   │   │   │   ├── img-soon-6.svg
│   │   │   │   │   ├── img-soon-7.svg
│   │   │   │   │   ├── img-soon-8.svg
│   │   │   │   │   ├── img-soon-bg-grid-dark.svg
│   │   │   │   │   ├── img-soon-bg-grid.svg
│   │   │   │   │   ├── img-soon-bg.svg
│   │   │   │   │   ├── img-soon-block.svg
│   │   │   │   │   ├── img-soon-blue-block.svg
│   │   │   │   │   ├── img-soon-grid-dark.svg
│   │   │   │   │   ├── img-soon-grid.svg
│   │   │   │   │   └── img-soon-purple-block.svg
│   │   │   │   ├── pages
│   │   │   │   │   ├── card-discover.png
│   │   │   │   │   ├── card-master.png
│   │   │   │   │   ├── card-visa.png
│   │   │   │   │   ├── img-catalog1.png
│   │   │   │   │   ├── img-catalog2.png
│   │   │   │   │   └── img-catalog3.png
│   │   │   │   ├── upload
│   │   │   │   │   └── upload.svg
│   │   │   │   ├── users
│   │   │   │   │   ├── avatar-1.png
│   │   │   │   │   ├── avatar-10.png
│   │   │   │   │   ├── avatar-11.png
│   │   │   │   │   ├── avatar-12.png
│   │   │   │   │   ├── avatar-2.png
│   │   │   │   │   ├── avatar-3.png
│   │   │   │   │   ├── avatar-4.png
│   │   │   │   │   ├── avatar-5.png
│   │   │   │   │   ├── avatar-6.png
│   │   │   │   │   ├── avatar-7.png
│   │   │   │   │   ├── avatar-8.png
│   │   │   │   │   ├── avatar-9.png
│   │   │   │   │   ├── img-user.png
│   │   │   │   │   ├── profile.png
│   │   │   │   │   └── user-round.svg
│   │   │   │   └── widget
│   │   │   │       ├── australia.jpg
│   │   │   │       ├── brazil.jpg
│   │   │   │       ├── dashboard-1.jpg
│   │   │   │       ├── dashboard-2.jpg
│   │   │   │       ├── germany.jpg
│   │   │   │       ├── phone-1.jpg
│   │   │   │       ├── phone-2.jpg
│   │   │   │       ├── phone-3.jpg
│   │   │   │       ├── phone-4.jpg
│   │   │   │       ├── prod1.jpg
│   │   │   │       ├── prod2.jpg
│   │   │   │       ├── prod3.jpg
│   │   │   │       ├── prod4.jpg
│   │   │   │       ├── uk.jpg
│   │   │   │       └── usa.jpg
│   │   │   └── scss
│   │   │       ├── _liquidation-bars.scss
│   │   │       ├── _sonic-dashboard.scss
│   │   │       ├── _sonic-header.scss
│   │   │       ├── _sonic-themes.scss
│   │   │       ├── _sonic-titles.scss
│   │   │       ├── _theme1.module.scss
│   │   │       ├── _theme2.module.scss
│   │   │       ├── _theme3.module.scss
│   │   │       ├── _theme4.module.scss
│   │   │       ├── _theme5.module.scss
│   │   │       ├── _theme6.module.scss
│   │   │       ├── _themes-vars.module.scss
│   │   │       ├── index.scss
│   │   │       ├── scrollbar.scss
│   │   │       ├── style.scss
│   │   │       └── yet-another-react-lightbox.scss
│   │   ├── components
│   │   │   ├── AppGrid.jsx
│   │   │   ├── AssetLogo.jsx
│   │   │   ├── CompositionPieCard
│   │   │   │   └── CompositionPieCard.jsx
│   │   │   ├── MarketMovementCard.jsx
│   │   │   ├── PerformanceGraphCard
│   │   │   │   ├── PerformanceGraphCard.jsx
│   │   │   │   └── chart-data
│   │   │   │       └── market-share-area-chart.jsx
│   │   │   ├── PortfolioSessionCard
│   │   │   │   └── PortfolioSessionCard.jsx
│   │   │   ├── PositionListCard
│   │   │   │   └── PositionListCard.jsx
│   │   │   ├── PositionPieCard
│   │   │   │   └── PositionPieCard.jsx
│   │   │   ├── ProfitRiskHeaderBadges.jsx
│   │   │   ├── StatusRail
│   │   │   │   ├── DashboardToggle.jsx
│   │   │   │   ├── OperationsBar.jsx
│   │   │   │   ├── PortfolioBar.jsx
│   │   │   │   ├── StatCard.jsx
│   │   │   │   ├── StatusRail.jsx
│   │   │   │   └── cardData.jsx
│   │   │   ├── TraderListCard
│   │   │   │   └── TraderListCard.jsx
│   │   │   ├── dashboard-grid
│   │   │   │   ├── DashboardGrid.jsx
│   │   │   │   ├── GridSection.jsx
│   │   │   │   ├── GridSlot.jsx
│   │   │   │   └── registerWidget.js
│   │   │   ├── jupiter
│   │   │   │   └── Perps
│   │   │   │       ├── MarketsPanel.jsx
│   │   │   │       └── PositionsPanel.jsx
│   │   │   ├── old
│   │   │   │   ├── DashboardToggle.jsx
│   │   │   │   ├── OperationsBar.jsx
│   │   │   │   ├── PortfolioBar.jsx
│   │   │   │   └── StatCard.jsx
│   │   │   ├── shared
│   │   │   │   └── Currency.jsx
│   │   │   └── wallets
│   │   │       └── VerifiedCells.jsx
│   │   ├── config.js
│   │   ├── contexts
│   │   │   ├── AWSCognitoContext.jsx
│   │   │   ├── Auth0Context.jsx
│   │   │   ├── ConfigContext.jsx
│   │   │   ├── FirebaseContext.jsx
│   │   │   ├── JWTContext.jsx
│   │   │   └── SupabaseContext.jsx
│   │   ├── data
│   │   │   └── wallets.js
│   │   ├── hedge-report
│   │   │   ├── App.tsx
│   │   │   ├── api
│   │   │   │   └── hooks.ts
│   │   │   ├── components
│   │   │   │   ├── HedgeEvaluator.tsx
│   │   │   │   └── PositionsTable.tsx
│   │   │   ├── main.tsx
│   │   │   ├── pages
│   │   │   │   └── HedgeReportPage.tsx
│   │   │   ├── styles
│   │   │   │   ├── hedge_labs.css
│   │   │   │   ├── hedge_report.css
│   │   │   │   └── sonic_themes.css
│   │   │   └── types
│   │   │       └── position.ts
│   │   ├── hooks
│   │   │   ├── useAuth.js
│   │   │   ├── useConfig.js
│   │   │   ├── useLocalStorage.js
│   │   │   ├── useMenuCollapse.js
│   │   │   ├── useRunSonicMonitor.js
│   │   │   ├── useScriptRef.js
│   │   │   ├── useSonicStatusPolling.js
│   │   │   └── useXCom.js
│   │   ├── index.jsx
│   │   ├── layout
│   │   │   ├── Customization
│   │   │   │   ├── BorderRadius.jsx
│   │   │   │   ├── BoxContainer.jsx
│   │   │   │   ├── FontFamily.jsx
│   │   │   │   ├── InputFilled.jsx
│   │   │   │   ├── Layout.jsx
│   │   │   │   ├── MenuOrientation.jsx
│   │   │   │   ├── PresetColor.jsx
│   │   │   │   ├── SidebarDrawer.jsx
│   │   │   │   ├── ThemeMode.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── MainLayout
│   │   │   │   ├── Footer.jsx
│   │   │   │   ├── Header
│   │   │   │   │   ├── CycloneRunSection
│   │   │   │   │   │   ├── CycloneRunSection.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── FullScreenSection
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── LocalizationSection
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── MegaMenuSection
│   │   │   │   │   │   ├── Banner.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── MobileSection
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── NotificationSection
│   │   │   │   │   │   ├── NotificationList.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── SearchSection
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── SettingsSection
│   │   │   │   │   │   ├── UpgradePlanCard.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── ThemeModeSection
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── TimerSection
│   │   │   │   │   │   ├── DonutCountdown.jsx
│   │   │   │   │   │   └── TimerSection.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── HorizontalBar.jsx
│   │   │   │   ├── LogoSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── MainContentStyled.js
│   │   │   │   ├── MenuList
│   │   │   │   │   ├── NavCollapse
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── NavGroup
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── NavItem
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Sidebar
│   │   │   │   │   ├── MenuCard
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── MiniDrawerStyled.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── MinimalLayout
│   │   │   │   └── index.jsx
│   │   │   ├── NavMotion.jsx
│   │   │   └── NavigationScroll.jsx
│   │   ├── lib
│   │   │   └── api
│   │   │       └── sonicClient.ts
│   │   ├── menu-items
│   │   │   ├── alert-thresholds.js
│   │   │   ├── analytics.js
│   │   │   ├── dashboard-default.js
│   │   │   ├── index.js
│   │   │   ├── jupiter.js
│   │   │   ├── kanban.js
│   │   │   ├── monitor-manager.js
│   │   │   ├── overview.js
│   │   │   ├── pages.js
│   │   │   ├── positions.js
│   │   │   ├── sonic-labs.js
│   │   │   ├── sonic.js
│   │   │   ├── traderFactory.js
│   │   │   ├── traderShop.js
│   │   │   └── wallet-manager.js
│   │   ├── reportWebVitals.js
│   │   ├── routes
│   │   │   ├── AuthenticationRoutes.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── LoginRoutes.jsx
│   │   │   ├── MainRoutes.jsx
│   │   │   ├── TraderShopRoutes.jsx
│   │   │   └── index.jsx
│   │   ├── serviceWorker.jsx
│   │   ├── store
│   │   │   ├── accountReducer.js
│   │   │   ├── actions.js
│   │   │   ├── constant.js
│   │   │   ├── index.js
│   │   │   ├── reducer.js
│   │   │   └── slices
│   │   │       ├── alertThresholds.js
│   │   │       ├── kanban.js
│   │   │       └── snackbar.js
│   │   ├── tailwind.css
│   │   ├── themes
│   │   │   ├── compStyleOverride.jsx
│   │   │   ├── index.jsx
│   │   │   ├── overrides
│   │   │   │   ├── Chip.jsx
│   │   │   │   └── index.js
│   │   │   ├── palette.jsx
│   │   │   ├── shadows.jsx
│   │   │   └── typography.jsx
│   │   ├── ui-component
│   │   │   ├── Loadable.jsx
│   │   │   ├── Loader.jsx
│   │   │   ├── Locales.jsx
│   │   │   ├── Logo.jsx
│   │   │   ├── RTLLayout.jsx
│   │   │   ├── cards
│   │   │   │   ├── AnalyticsChartCard.jsx
│   │   │   │   ├── AttachmentCard.jsx
│   │   │   │   ├── AuthFooter.jsx
│   │   │   │   ├── AuthSlider.jsx
│   │   │   │   ├── BackgroundPattern1.jsx
│   │   │   │   ├── BackgroundPattern2.jsx
│   │   │   │   ├── BillCard.jsx
│   │   │   │   ├── CardSecondaryAction.jsx
│   │   │   │   ├── ContactCard.jsx
│   │   │   │   ├── ContactList.jsx
│   │   │   │   ├── FloatingCart.jsx
│   │   │   │   ├── FollowerCard.jsx
│   │   │   │   ├── FriendRequestCard.jsx
│   │   │   │   ├── FriendsCard.jsx
│   │   │   │   ├── FullWidthPaper.jsx
│   │   │   │   ├── GalleryCard.jsx
│   │   │   │   ├── HoverDataCard.jsx
│   │   │   │   ├── HoverSocialCard.jsx
│   │   │   │   ├── IconNumberCard.jsx
│   │   │   │   ├── MainCard.jsx
│   │   │   │   ├── ProductCard.jsx
│   │   │   │   ├── ProductReview.jsx
│   │   │   │   ├── ReportCard.jsx
│   │   │   │   ├── RevenueCard.jsx
│   │   │   │   ├── RoundIconCard.jsx
│   │   │   │   ├── SalesLineChartCard.jsx
│   │   │   │   ├── SeoChartCard.jsx
│   │   │   │   ├── SideIconCard.jsx
│   │   │   │   ├── Skeleton
│   │   │   │   │   ├── EarningCard.jsx
│   │   │   │   │   ├── ImagePlaceholder.jsx
│   │   │   │   │   ├── PopularCard.jsx
│   │   │   │   │   ├── ProductPlaceholder.jsx
│   │   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   │   └── TotalIncomeCard.jsx
│   │   │   │   ├── SubCard.jsx
│   │   │   │   ├── TotalIncomeDarkCard.jsx
│   │   │   │   ├── TotalIncomeLightCard.jsx
│   │   │   │   ├── TotalLineChartCard.jsx
│   │   │   │   ├── TotalValueCard.jsx
│   │   │   │   ├── UserCountCard.jsx
│   │   │   │   ├── UserDetailsCard.jsx
│   │   │   │   ├── UserProfileCard.jsx
│   │   │   │   ├── UserSimpleCard.jsx
│   │   │   │   ├── ValueToCollateralChartCard.jsx
│   │   │   │   ├── charts
│   │   │   │   │   └── ValueToCollateralChartCard.jsx
│   │   │   │   └── positions
│   │   │   │       └── PositionsTableCard.jsx
│   │   │   ├── containers
│   │   │   │   └── DashRowContainer.jsx
│   │   │   ├── extended
│   │   │   │   ├── Accordion.jsx
│   │   │   │   ├── AnimateButton.jsx
│   │   │   │   ├── AppBar.jsx
│   │   │   │   ├── Avatar.jsx
│   │   │   │   ├── Breadcrumbs.jsx
│   │   │   │   ├── Form
│   │   │   │   │   ├── FormControl.jsx
│   │   │   │   │   ├── FormControlSelect.jsx
│   │   │   │   │   └── InputLabel.jsx
│   │   │   │   ├── ImageList.jsx
│   │   │   │   ├── Snackbar.jsx
│   │   │   │   ├── Transitions.jsx
│   │   │   │   └── notistack
│   │   │   │       ├── ColorVariants.jsx
│   │   │   │       ├── CustomComponent.jsx
│   │   │   │       ├── Dense.jsx
│   │   │   │       ├── DismissSnackBar.jsx
│   │   │   │       ├── HideDuration.jsx
│   │   │   │       ├── IconVariants.jsx
│   │   │   │       ├── MaxSnackbar.jsx
│   │   │   │       ├── PositioningSnackbar.jsx
│   │   │   │       ├── PreventDuplicate.jsx
│   │   │   │       ├── SnackBarAction.jsx
│   │   │   │       ├── TransitionBar.jsx
│   │   │   │       └── index.jsx
│   │   │   ├── fun
│   │   │   │   └── FunCard.jsx
│   │   │   ├── liquidation
│   │   │   │   ├── LiqRow.jsx
│   │   │   │   └── LiquidationBars.jsx
│   │   │   ├── rails
│   │   │   │   └── StatusRail.jsx
│   │   │   ├── status-rail
│   │   │   │   ├── StatusCard.jsx
│   │   │   │   ├── StatusRail.jsx
│   │   │   │   ├── cardData.js
│   │   │   │   ├── cardData.jsx
│   │   │   │   └── statusRail.scss
│   │   │   ├── third-party
│   │   │   │   ├── Notistack.jsx
│   │   │   │   └── dropzone
│   │   │   │       ├── Avatar.jsx
│   │   │   │       ├── FilePreview.jsx
│   │   │   │       ├── MultiFile.jsx
│   │   │   │       ├── PlaceHolderContent.jsx
│   │   │   │       ├── RejectionFile.jsx
│   │   │   │       └── SingleFile.jsx
│   │   │   ├── thresholds
│   │   │   │   ├── CooldownTable.jsx
│   │   │   │   └── ThresholdTable.jsx
│   │   │   └── wallet
│   │   │       ├── WalletFormModal.jsx
│   │   │       ├── WalletPieCard.jsx
│   │   │       └── WalletTable.jsx
│   │   ├── utils
│   │   │   ├── axios.js
│   │   │   ├── getDropzoneData.js
│   │   │   ├── getImageUrl.js
│   │   │   ├── hedgeColors.js
│   │   │   ├── locales
│   │   │   │   ├── en.json
│   │   │   │   ├── fr.json
│   │   │   │   ├── ro.json
│   │   │   │   └── zh.json
│   │   │   ├── password-strength.js
│   │   │   └── route-guard
│   │   │       ├── AuthGuard.jsx
│   │   │       └── GuestGuard.jsx
│   │   ├── views
│   │   │   ├── alertThresholds
│   │   │   │   ├── AddThresholdDialog.jsx
│   │   │   │   ├── AlertThresholdsPage.jsx
│   │   │   │   ├── ThresholdsTable.jsx
│   │   │   │   ├── icons.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── dashboard
│   │   │   │   ├── Analytics
│   │   │   │   │   ├── index - Copy (2).jsx
│   │   │   │   │   ├── index - Copy.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── CompositionPieCard.jsx
│   │   │   │   ├── Default
│   │   │   │   │   ├── BajajAreaChartCard.jsx
│   │   │   │   │   ├── EarningCard.jsx
│   │   │   │   │   ├── PopularCard.jsx
│   │   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   │   ├── TotalOrderLineChartCard.jsx
│   │   │   │   │   ├── chart-data
│   │   │   │   │   │   ├── bajaj-area-chart.jsx
│   │   │   │   │   │   ├── total-growth-bar-chart.jsx
│   │   │   │   │   │   ├── total-order-month-line-chart.jsx
│   │   │   │   │   │   └── total-order-year-line-chart.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── PerformanceGraphCard.jsx
│   │   │   │   ├── PositionListCard.jsx
│   │   │   │   ├── ProfitRiskHeaderBadges.jsx
│   │   │   │   ├── TraderListCard.jsx
│   │   │   │   ├── VerticalMonitorSummaryCard.jsx
│   │   │   │   ├── analytics-wireframe.json
│   │   │   │   ├── chart-data
│   │   │   │   │   └── market-share-area-chart.jsx
│   │   │   │   └── market-share-area-chart.jsx
│   │   │   ├── debug
│   │   │   │   └── DatabaseViewer.jsx
│   │   │   ├── forms
│   │   │   │   ├── chart
│   │   │   │   │   ├── Apexchart
│   │   │   │   │   │   ├── ApexAreaChart.jsx
│   │   │   │   │   │   ├── ApexBarChart.jsx
│   │   │   │   │   │   ├── ApexColumnChart.jsx
│   │   │   │   │   │   ├── ApexLineChart.jsx
│   │   │   │   │   │   ├── ApexMixedChart.jsx
│   │   │   │   │   │   ├── ApexPieChart.jsx
│   │   │   │   │   │   ├── ApexPolarChart.jsx
│   │   │   │   │   │   ├── ApexRedialChart.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   └── OrgChart
│   │   │   │   │       ├── Card.jsx
│   │   │   │   │       ├── DataCard.jsx
│   │   │   │   │       ├── LinkedIn.jsx
│   │   │   │   │       ├── MeetIcon.jsx
│   │   │   │   │       ├── SkypeIcon.jsx
│   │   │   │   │       └── index.jsx
│   │   │   │   ├── components
│   │   │   │   │   ├── AutoComplete.jsx
│   │   │   │   │   ├── Button.jsx
│   │   │   │   │   ├── Checkbox.jsx
│   │   │   │   │   ├── DateTime
│   │   │   │   │   │   ├── CustomDateTime.jsx
│   │   │   │   │   │   ├── LandscapeDateTime.jsx
│   │   │   │   │   │   ├── ViewRendererDateTime.jsx
│   │   │   │   │   │   ├── ViewsDateTimePicker.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── Radio.jsx
│   │   │   │   │   ├── Slider
│   │   │   │   │   │   ├── BasicSlider.jsx
│   │   │   │   │   │   ├── DisableSlider.jsx
│   │   │   │   │   │   ├── LabelSlider.jsx
│   │   │   │   │   │   ├── PopupSlider.jsx
│   │   │   │   │   │   ├── StepSlider.jsx
│   │   │   │   │   │   ├── VerticalSlider.jsx
│   │   │   │   │   │   ├── VolumeSlider.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── Switch.jsx
│   │   │   │   │   └── TextField.jsx
│   │   │   │   ├── data-grid
│   │   │   │   │   ├── ColumnGroups
│   │   │   │   │   │   ├── BasicColumnGroup.jsx
│   │   │   │   │   │   ├── CustomColumnGroup.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── ColumnMenu
│   │   │   │   │   │   ├── AddMenuItem.jsx
│   │   │   │   │   │   ├── ColumnMenu.jsx
│   │   │   │   │   │   ├── CustomMenu.jsx
│   │   │   │   │   │   ├── DisableMenu.jsx
│   │   │   │   │   │   ├── HideMenuItem.jsx
│   │   │   │   │   │   ├── OverrideMenu.jsx
│   │   │   │   │   │   ├── ReorderingMenu.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── ColumnVirtualization
│   │   │   │   │   │   ├── Virtualization.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── ColumnVisibility
│   │   │   │   │   │   ├── ControlledVisibility.jsx
│   │   │   │   │   │   ├── InitializeColumnVisibility.jsx
│   │   │   │   │   │   ├── VisibilityPanel.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── DataGridBasic
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── InLineEditing
│   │   │   │   │   │   ├── AutoStop.jsx
│   │   │   │   │   │   ├── ConfirmationSave.jsx
│   │   │   │   │   │   ├── Controlled.jsx
│   │   │   │   │   │   ├── CustomEdit.jsx
│   │   │   │   │   │   ├── DisableEditing.jsx
│   │   │   │   │   │   ├── EditableColumn.jsx
│   │   │   │   │   │   ├── EditableRow.jsx
│   │   │   │   │   │   ├── EditingEvents.jsx
│   │   │   │   │   │   ├── FullFeatured.jsx
│   │   │   │   │   │   ├── ParserSetter.jsx
│   │   │   │   │   │   ├── ServerValidation.jsx
│   │   │   │   │   │   ├── Validation.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── QuickFilter
│   │   │   │   │   │   ├── CustomFilter.jsx
│   │   │   │   │   │   ├── ExcludeHiddenColumns.jsx
│   │   │   │   │   │   ├── Initialize.jsx
│   │   │   │   │   │   ├── ParsingValues.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   └── SaveRestoreState
│   │   │   │   │       ├── InitialState.jsx
│   │   │   │   │       ├── UseGridSelector.jsx
│   │   │   │   │       └── index.jsx
│   │   │   │   ├── forms-validation
│   │   │   │   │   ├── AutocompleteForms.jsx
│   │   │   │   │   ├── CheckboxForms.jsx
│   │   │   │   │   ├── InstantFeedback.jsx
│   │   │   │   │   ├── LoginForms.jsx
│   │   │   │   │   ├── RadioGroupForms.jsx
│   │   │   │   │   ├── SelectForms.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── forms-wizard
│   │   │   │   │   ├── BasicWizard
│   │   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   │   ├── Review.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── ValidationWizard
│   │   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   │   ├── Review.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── layouts
│   │   │   │   │   ├── ActionBar.jsx
│   │   │   │   │   ├── Layouts.jsx
│   │   │   │   │   ├── MultiColumnForms.jsx
│   │   │   │   │   └── StickyActionBar.jsx
│   │   │   │   ├── plugins
│   │   │   │   │   ├── AutoComplete.jsx
│   │   │   │   │   ├── Clipboard.jsx
│   │   │   │   │   ├── Dropzone.jsx
│   │   │   │   │   ├── Editor.jsx
│   │   │   │   │   ├── Mask.jsx
│   │   │   │   │   ├── Modal
│   │   │   │   │   │   ├── ServerModal.jsx
│   │   │   │   │   │   ├── SimpleModal.jsx
│   │   │   │   │   │   └── index.jsx
│   │   │   │   │   ├── Recaptcha.jsx
│   │   │   │   │   └── Tooltip.jsx
│   │   │   │   └── tables
│   │   │   │       ├── TableBasic.jsx
│   │   │   │       ├── TableCollapsible.jsx
│   │   │   │       ├── TableData.jsx
│   │   │   │       ├── TableDense.jsx
│   │   │   │       ├── TableEnhanced.jsx
│   │   │   │       ├── TableExports.jsx
│   │   │   │       ├── TableStickyHead.jsx
│   │   │   │       └── TablesCustomized.jsx
│   │   │   ├── hedgeReport
│   │   │   │   ├── HedgeReportPage.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── jupiter
│   │   │   │   └── JupiterPage.jsx
│   │   │   ├── kanban
│   │   │   │   ├── Backlogs
│   │   │   │   │   ├── AddItem.jsx
│   │   │   │   │   ├── AddStory.jsx
│   │   │   │   │   ├── AddStoryComment.jsx
│   │   │   │   │   ├── AlertStoryDelete.jsx
│   │   │   │   │   ├── EditStory.jsx
│   │   │   │   │   ├── Items.jsx
│   │   │   │   │   ├── StoryComment.jsx
│   │   │   │   │   ├── UserStory.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Board
│   │   │   │   │   ├── AddColumn.jsx
│   │   │   │   │   ├── AddItem.jsx
│   │   │   │   │   ├── AddItemComment.jsx
│   │   │   │   │   ├── AlertColumnDelete.jsx
│   │   │   │   │   ├── AlertItemDelete.jsx
│   │   │   │   │   ├── Columns.jsx
│   │   │   │   │   ├── EditColumn.jsx
│   │   │   │   │   ├── EditItem.jsx
│   │   │   │   │   ├── ItemComment.jsx
│   │   │   │   │   ├── ItemDetails.jsx
│   │   │   │   │   ├── Items.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── monitorManager
│   │   │   │   ├── LiquidationMonitorCard.jsx
│   │   │   │   ├── MarketMonitorCard.jsx
│   │   │   │   ├── MonitorManager.jsx
│   │   │   │   ├── MonitorUpdateBar.jsx
│   │   │   │   ├── ProfitMonitorCard.jsx
│   │   │   │   └── SonicMonitorCard.jsx
│   │   │   ├── overview
│   │   │   │   └── index.jsx
│   │   │   ├── pages
│   │   │   │   ├── authentication
│   │   │   │   │   ├── AuthCardWrapper.jsx
│   │   │   │   │   ├── AuthWrapper1.jsx
│   │   │   │   │   ├── AuthWrapper2.jsx
│   │   │   │   │   ├── CheckMail.jsx
│   │   │   │   │   ├── CodeVerification.jsx
│   │   │   │   │   ├── ForgotPassword.jsx
│   │   │   │   │   ├── Login.jsx
│   │   │   │   │   ├── LoginProvider.jsx
│   │   │   │   │   ├── Register.jsx
│   │   │   │   │   ├── ResetPassword.jsx
│   │   │   │   │   ├── ViewOnlyAlert.jsx
│   │   │   │   │   ├── auth0
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── aws
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── firebase
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   ├── AuthResetPassword.jsx
│   │   │   │   │   │   └── FirebaseSocial.jsx
│   │   │   │   │   ├── jwt
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   └── supabase
│   │   │   │   │       ├── AuthCodeVerification.jsx
│   │   │   │   │       ├── AuthForgotPassword.jsx
│   │   │   │   │       ├── AuthLogin.jsx
│   │   │   │   │       ├── AuthRegister.jsx
│   │   │   │   │       └── AuthResetPassword.jsx
│   │   │   │   └── maintenance
│   │   │   │       ├── ComingSoon
│   │   │   │       │   ├── ComingSoon1
│   │   │   │       │   │   ├── MailerSubscriber.jsx
│   │   │   │       │   │   ├── Slider.jsx
│   │   │   │       │   │   └── index.jsx
│   │   │   │       │   └── ComingSoon2.jsx
│   │   │   │       ├── Error.jsx
│   │   │   │       ├── Error500.jsx
│   │   │   │       ├── Forbidden.jsx
│   │   │   │       └── UnderConstruction.jsx
│   │   │   ├── positions
│   │   │   │   ├── LiquidationBarsCard.jsx
│   │   │   │   ├── PositionTableCard.jsx
│   │   │   │   ├── PositionsPage.jsx
│   │   │   │   ├── SidePanelWidthSlider.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── sonic
│   │   │   │   ├── index.jsx
│   │   │   │   └── index_BU.jsx
│   │   │   ├── sonicLabs
│   │   │   │   ├── SonicLabsPage.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── traderFactory
│   │   │   │   ├── TraderBar.jsx
│   │   │   │   ├── TraderCard.css
│   │   │   │   ├── TraderCard.jsx
│   │   │   │   └── TraderFactoryPage.jsx
│   │   │   ├── traderShop
│   │   │   │   ├── QuickImportStarWars.jsx
│   │   │   │   ├── TraderEnhancedTable.jsx
│   │   │   │   ├── TraderFormDrawer.jsx
│   │   │   │   ├── TraderShopList.jsx
│   │   │   │   ├── hooks.js
│   │   │   │   ├── index.jsx
│   │   │   │   └── sampleTraders.json
│   │   │   ├── utilities
│   │   │   │   ├── Animation.jsx
│   │   │   │   ├── Color.jsx
│   │   │   │   ├── Grid
│   │   │   │   │   ├── AutoGrid.jsx
│   │   │   │   │   ├── BasicGrid.jsx
│   │   │   │   │   ├── ColumnsGrid.jsx
│   │   │   │   │   ├── ComplexGrid.jsx
│   │   │   │   │   ├── GridItem.jsx
│   │   │   │   │   ├── MultipleBreakPoints.jsx
│   │   │   │   │   ├── NestedGrid.jsx
│   │   │   │   │   ├── SpacingGrid.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Shadow.jsx
│   │   │   │   └── Typography.jsx
│   │   │   ├── wallet
│   │   │   │   ├── BalanceBreakdownCard.jsx
│   │   │   │   └── WalletManager.jsx
│   │   │   ├── widget
│   │   │   │   ├── Chart
│   │   │   │   │   ├── ConversionsChartCard.jsx
│   │   │   │   │   ├── MarketSaleChartCard.jsx
│   │   │   │   │   ├── RevenueChartCard.jsx
│   │   │   │   │   ├── SatisfactionChartCard.jsx
│   │   │   │   │   ├── chart-data
│   │   │   │   │   │   ├── conversions-chart.jsx
│   │   │   │   │   │   ├── index.jsx
│   │   │   │   │   │   ├── market-sale-chart.jsx
│   │   │   │   │   │   ├── percentage-chart.jsx
│   │   │   │   │   │   ├── revenue-chart.jsx
│   │   │   │   │   │   ├── sale-chart-1.jsx
│   │   │   │   │   │   ├── satisfaction-chart.jsx
│   │   │   │   │   │   ├── seo-chart-1.jsx
│   │   │   │   │   │   ├── seo-chart-2.jsx
│   │   │   │   │   │   ├── seo-chart-3.jsx
│   │   │   │   │   │   ├── seo-chart-4.jsx
│   │   │   │   │   │   ├── seo-chart-5.jsx
│   │   │   │   │   │   ├── seo-chart-6.jsx
│   │   │   │   │   │   ├── seo-chart-7.jsx
│   │   │   │   │   │   ├── seo-chart-8.jsx
│   │   │   │   │   │   ├── seo-chart-9.jsx
│   │   │   │   │   │   ├── total-value-graph-1.jsx
│   │   │   │   │   │   ├── total-value-graph-2.jsx
│   │   │   │   │   │   └── total-value-graph-3.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Data
│   │   │   │   │   ├── ActiveTickets.jsx
│   │   │   │   │   ├── ApplicationSales.jsx
│   │   │   │   │   ├── FeedsCard.jsx
│   │   │   │   │   ├── IncomingRequests.jsx
│   │   │   │   │   ├── LatestCustomers.jsx
│   │   │   │   │   ├── LatestMessages.jsx
│   │   │   │   │   ├── LatestOrder.jsx
│   │   │   │   │   ├── LatestPosts.jsx
│   │   │   │   │   ├── NewCustomers.jsx
│   │   │   │   │   ├── ProductSales.jsx
│   │   │   │   │   ├── ProjectTable.jsx
│   │   │   │   │   ├── RecentTickets.jsx
│   │   │   │   │   ├── TasksCard.jsx
│   │   │   │   │   ├── TeamMembers.jsx
│   │   │   │   │   ├── ToDoList.jsx
│   │   │   │   │   ├── TotalRevenue.jsx
│   │   │   │   │   ├── TrafficSources.jsx
│   │   │   │   │   ├── UserActivity.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── Statistics
│   │   │   │       ├── CustomerSatisfactionCard.jsx
│   │   │   │       ├── IconGridCard.jsx
│   │   │   │       ├── ProjectTaskCard.jsx
│   │   │   │       ├── WeatherCard.jsx
│   │   │   │       └── index.jsx
│   │   │   └── xcomSettings
│   │   │       ├── XComSettings.jsx
│   │   │       └── components
│   │   │           └── ProviderAccordion.jsx
│   │   └── vite-env.d.js
│   ├── static
│   │   ├── images
│   │   │   ├── Wally.png
│   │   │   ├── __init__.py
│   │   │   ├── aave.jpg
│   │   │   ├── alert_wall.jpg
│   │   │   ├── boba_icon.jpg
│   │   │   ├── bobavault.jpg
│   │   │   ├── btc_logo.png
│   │   │   ├── bubba_icon.png
│   │   │   ├── c3po_icon.jpg
│   │   │   ├── c3povault.jpg
│   │   │   ├── chewbaccavault.jpg
│   │   │   ├── chewie_icon.jpg
│   │   │   ├── cityscape3.jpg
│   │   │   ├── container_wallpaper.jpg
│   │   │   ├── corner_icon.jpg
│   │   │   ├── corner_logo_owl.jpg
│   │   │   ├── corner_logos.jpg
│   │   │   ├── crypto_icon.jpg
│   │   │   ├── crypto_iconz.png
│   │   │   ├── database_wall.jpg
│   │   │   ├── error.png
│   │   │   ├── eth_logo.png
│   │   │   ├── jabba_icon.jpg
│   │   │   ├── jabba_icon.png
│   │   │   ├── jabbavault.jpg
│   │   │   ├── jupiter.jpg
│   │   │   ├── lando_icon.jpg
│   │   │   ├── landovault.jpg
│   │   │   ├── lawyer.jpg
│   │   │   ├── leia_icon.jpg
│   │   │   ├── leiavault.jpg
│   │   │   ├── logo.png
│   │   │   ├── logo2.png
│   │   │   ├── luke_icon.jpg
│   │   │   ├── lukevault.jpg
│   │   │   ├── monitor_wallpaper.jpg
│   │   │   ├── obi_icon.jpg
│   │   │   ├── obivault.jpg
│   │   │   ├── palpatine_icon.jpg
│   │   │   ├── palpatinevault.jpg
│   │   │   ├── r2d2_icon.jpg
│   │   │   ├── r2vault.jpg
│   │   │   ├── raydium.jpg
│   │   │   ├── sol_logo.png
│   │   │   ├── sonars.png
│   │   │   ├── sonic.png
│   │   │   ├── sonic_burst.png
│   │   │   ├── sonic_title.png
│   │   │   ├── space_wall4.jpg
│   │   │   ├── super_sonic.png
│   │   │   ├── sys_config_wall.jpg
│   │   │   ├── trader_wallpaper.jpg
│   │   │   ├── twilio.png
│   │   │   ├── unknown.png
│   │   │   ├── unknown_wallet.jpg
│   │   │   ├── vader_icon.jpg
│   │   │   ├── vadervault.jpg
│   │   │   ├── wallpaper2.jpg
│   │   │   ├── wallpaper2.png
│   │   │   ├── wallpaper4.jpg
│   │   │   ├── wallpaper5.jpg
│   │   │   ├── wallpaper6.jpg
│   │   │   ├── wallpaper_green.png
│   │   │   ├── wallpaper_grey_blue.jpg
│   │   │   ├── wallpapersden.jpg
│   │   │   ├── wally2.png
│   │   │   ├── yoda_icon.jpg
│   │   │   └── yodavault.jpg
│   │   └── sounds
│   │       ├── alert_liq.mp3
│   │       ├── death_spiral.mp3
│   │       ├── error.mp3
│   │       ├── fail.mp3
│   │       ├── level-up.mp3
│   │       ├── message_alert.mp3
│   │       ├── profit_alert.mp3
│   │       └── web_station_startup.mp3
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── vite.config.mjs
│   └── yarn.lock
├── idl
│   └── jupiter_perps.json
├── launch_pad.py
├── package-lock.json
├── package.json
├── patches
│   ├── LiquidationMonitorCard.patch
│   ├── MarketMonitorCard.patch
│   ├── MonitorManager.patch
│   ├── ProfitMonitorCard.patch
│   └── SonicMonitorCard.patch
├── requirements-dev.txt
├── requirements.txt
├── send_test_sms (2).py
├── send_test_sms.py
├── sonic_spec_bundle
│   ├── Makefile
│   ├── README_CODEX.md
│   ├── api
│   │   ├── __init__.py
│   │   ├── generate_openapi.py
│   │   ├── main.py
│   │   └── openapi.yaml
│   ├── docs
│   │   ├── actions
│   │   │   └── sonic_actions.json
│   │   ├── schemas
│   │   │   ├── README.md
│   │   │   ├── alert_create.json
│   │   │   ├── order.json
│   │   │   ├── order_create.json
│   │   │   └── position_adjust.json
│   │   ├── spec
│   │   │   ├── architecture.md
│   │   │   ├── codebase_map.md
│   │   │   ├── conventions.md
│   │   │   ├── domain_glossary.md
│   │   │   ├── master.md
│   │   │   ├── non_goals.md
│   │   │   ├── troubleshooting.md
│   │   │   ├── ui_contracts.md
│   │   │   └── workflows.md
│   │   └── teaching_pack
│   │       ├── 00_readme_first.md
│   │       ├── 01_master_index.md
│   │       ├── 03_workflows_core.md
│   │       └── 04_api_quick.md
│   └── scripts
│       ├── spec_sync.py
│       └── spec_validate.py
├── test_core
│   ├── __init__.py
│   ├── __main__.py
│   ├── celebrations.py
│   ├── codex_env.json
│   ├── conftest.py
│   ├── console_ui.py
│   ├── formatter.py
│   ├── icons.py
│   ├── pytest.ini
│   ├── reports
│   │   ├── .gitkeep
│   │   ├── C_alpha5_test_core_tests_test__.py_failures.txt
│   │   ├── C_alpha5_test_core_tests_test_hedge_._failures.txt
│   │   ├── C_alpha5_test_core_tests_test_hedges_._failures.txt
│   │   ├── C_sonic2_test_core_tests_test__.py_failures.txt
│   │   ├── C_sonic4_test_core_tests_test_alert_._failures.txt
│   │   ├── summary.json
│   │   └── test_hedge_failures.txt
│   ├── runner.py
│   ├── test_core.py
│   ├── test_core_spec.md
│   └── tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── system
│       │   ├── alert_limits.json
│       │   └── system_test_helpers.py
│       ├── test_active_totals.py
│       ├── test_alert_core_create_all.py
│       ├── test_alert_core_enrich_all.py
│       ├── test_alert_core_logging.py
│       ├── test_alert_core_new.py
│       ├── test_alert_creation_configurebility.py
│       ├── test_alert_disabled_creation.py
│       ├── test_alert_enrich_all_order.py
│       ├── test_alert_enrichment.py
│       ├── test_alert_evaluation_service.py
│       ├── test_alert_levels_save_db.py
│       ├── test_alert_logging.py
│       ├── test_alert_thresholds_api.py
│       ├── test_alerts_api.py
│       ├── test_batch_enrich_evaluate_pipeline.py
│       ├── test_blockchain_balance_service.py
│       ├── test_calc_services_at_price.py
│       ├── test_calculation_core_missing_db.py
│       ├── test_chat_gpt_bp_api.py
│       ├── test_config_loader_logging.py
│       ├── test_create_evaluate_portfolio_alerts.py
│       ├── test_cyclone_aggregate_positions.py
│       ├── test_cyclone_alerts.py
│       ├── test_cyclone_config_fallback.py
│       ├── test_cyclone_market_udpates.py
│       ├── test_cyclone_position_updates.py
│       ├── test_cyclone_profit_badge_reset.py
│       ├── test_cyclone_run_cycle_position_updates.py
│       ├── test_cyclone_trader_snapshot.py
│       ├── test_dashboard_collateral.py
│       ├── test_dashboard_wallet_links.py
│       ├── test_database_recovery.py
│       ├── test_datalocker_close_resets_instance.py
│       ├── test_db_portfolio_alert_toggle.py
│       ├── test_dl_trader_manager.py
│       ├── test_enrich_portfolio.py
│       ├── test_enrichment_travel_percent.py
│       ├── test_formatter.py
│       ├── test_fun_api.py
│       ├── test_fuzzy_wuzzy.py
│       ├── test_gpt_bp_api.py
│       ├── test_gpt_context_service.py
│       ├── test_gpt_strategies.py
│       ├── test_hedge_auto_wizard.py
│       ├── test_hedge_calc_services.py
│       ├── test_hedge_calculator_page.py
│       ├── test_hedge_core_linking.py
│       ├── test_hedge_core_unlink.py
│       ├── test_hedge_eval_api.py
│       ├── test_hedge_liq_distance.py
│       ├── test_hottest_trader_api.py
│       ├── test_inactive_wallet_filter.py
│       ├── test_inactive_wallet_services.py
│       ├── test_insert_wallets.py
│       ├── test_invalid_data_locker.py
│       ├── test_jupiter_integration_imports.py
│       ├── test_jupiter_service.py
│       ├── test_jupiter_trigger_service.py
│       ├── test_launch_pad_goals.py
│       ├── test_launch_pad_recover.py
│       ├── test_launch_pad_web.py
│       ├── test_learning_bp_api.py
│       ├── test_learning_db_clear.py
│       ├── test_learning_db_subsystem.py
│       ├── test_modifiers_loading.py
│       ├── test_monitor_heat_api.py
│       ├── test_monitor_profit_total_api.py
│       ├── test_monitor_snooze.py
│       ├── test_monitor_travel_api.py
│       ├── test_notification_routing.py
│       ├── test_operations_monitor.py
│       ├── test_oracle_core_component.py
│       ├── test_oracle_data_service.py
│       ├── test_oracle_monitor.py
│       ├── test_oracle_persona_query.py
│       ├── test_order_engine_atomic.py
│       ├── test_order_factory_api.py
│       ├── test_persona_loading.py
│       ├── test_portfolio_alert_data_creation.py
│       ├── test_position_core_crud.py
│       ├── test_position_core_e2e.py
│       ├── test_position_core_enrich.py
│       ├── test_position_core_service.py
│       ├── test_position_sync_service.py
│       ├── test_positions_heat_metric.py
│       ├── test_positions_heat_metric_default_strategy.py
│       ├── test_positions_routes.py
│       ├── test_positions_topic_handler.py
│       ├── test_price_sync_service.py
│       ├── test_profit_alert_logging.py
│       ├── test_profit_badge_routes.py
│       ├── test_profit_monitor.py
│       ├── test_prune_stale_positions.py
│       ├── test_risk_monitor.py
│       ├── test_risk_thresholds_page.py
│       ├── test_run_glob.py
│       ├── test_runner_celebration.py
│       ├── test_runner_failures.py
│       ├── test_runner_wildcard.py
│       ├── test_schema_validation_service.py
│       ├── test_sol_position_enrichment.py
│       ├── test_sonic_app_launch_route.py
│       ├── test_sonic_header_sleep.py
│       ├── test_sonic_header_toggle.py
│       ├── test_startup_service_alert_thresholds.py
│       ├── test_startup_service_env.py
│       ├── test_startup_service_wallet.py
│       ├── test_system_api_routes.py
│       ├── test_system_api_status.py
│       ├── test_system_core_connectivity.py
│       ├── test_system_vars_default.py
│       ├── test_threshold_import.py
│       ├── test_threshold_progress.py
│       ├── test_trader_bp.py
│       ├── test_trader_core.py
│       ├── test_trader_core_crud.py
│       ├── test_trader_loader.py
│       ├── test_trader_update_service.py
│       ├── test_trader_wallet_heat.py
│       ├── test_transaction_service.py
│       ├── test_travel_badge_value.py
│       ├── test_travel_percent_seed.py
│       ├── test_twilio_sms_sender.py
│       ├── test_voice_service.py
│       ├── test_wallet_core_balance.py
│       ├── test_wallet_import_passphrase.py
│       ├── test_wallets.py
│       ├── test_xcom_config_service_alias.py
│       └── testz_celebrations.py
├── tests
│   ├── auto_core
│   │   ├── test_jupiter_connect.py
│   │   ├── test_playwright_extension.py
│   │   └── test_web_browser_request.py
│   ├── conftest.py
│   ├── golden
│   │   ├── test_liquidation_alerts.py
│   │   ├── test_orders_create.py
│   │   └── test_positions_adjust.py
│   ├── monitor
│   │   └── test_market_movement.py
│   ├── monitor_core
│   │   └── test_market_monitor.py
│   ├── positions
│   │   ├── test_position_crud.py
│   │   └── test_wallet_reconcile.py
│   ├── test_alert_thresholds_api.py
│   ├── test_clear_inactive_alerts.py
│   ├── test_clear_positions_keeps_portfolio.py
│   ├── test_console_title.py
│   ├── test_database_threading.py
│   ├── test_db_admin_api.py
│   ├── test_fun_api.py
│   ├── test_liquid_monitor.py
│   ├── test_liquid_monitor_config_seed.py
│   ├── test_market_monitor_config_seed.py
│   ├── test_market_route.py
│   ├── test_monitor_api_adapter.py
│   ├── test_monitor_core_status.py
│   ├── test_monitor_ledger_last_entry.py
│   ├── test_monitor_ledger_timestamp.py
│   ├── test_monitor_settings_api.py
│   ├── test_monitor_status.py
│   ├── test_monitor_status_api.py
│   ├── test_orders_api.py
│   ├── test_portfolio_fallback.py
│   ├── test_portfolio_snapshot.py
│   ├── test_portfolio_update_entry.py
│   ├── test_portfolio_update_snapshot.py
│   ├── test_positions_adjust_api.py
│   ├── test_positions_api.py
│   ├── test_session_api.py
│   ├── test_sessions.py
│   ├── test_sonic_monitor.py
│   ├── test_sound_service.py
│   ├── test_sync_session_update.py
│   ├── test_traders_api.py
│   ├── test_wallet_cli.py
│   ├── test_wallets_api.py
│   ├── test_xcom_config_env.py
│   ├── test_xcom_providers_merge.py
│   ├── test_xcom_providers_seed.py
│   └── test_xcom_status_service_sound.py
├── twilio_run.py
├── twilio_verify.py
├── wallet_balances.py
└── wallet_cli.py

235 directories, 1468 files
```
