# Alert System Specification

This document describes the codebase for the Sonic1 alert system. It consolidates the repository map and summarizes the purpose of each major file and directory in both the backend and frontend.

## Repository Map

```txt
sonic1/
├── backend
│   ├── config
│   │   ├── __init__.py
│   │   ├── active_traders.json
│   │   ├── alert_thresholds.json
│   │   ├── comm_config.json
│   │   ├── config_loader.py
│   │   ├── sonic_config.json
│   │   ├── sonic_sauce.json
│   │   └── theme_config.json
│   ├── console
│   │   ├── __init__.py
│   │   ├── cyclone_console.py
│   │   └── cyclone_console_service.py
│   ├── controllers
│   │   ├── __init__.py
│   │   ├── cyclone_controller.py
│   │   ├── logic.py
│   │   └── monitor_controller.py
│   ├── core
│   │   ├── alert_core
│   │   │   ├── config
│   │   │   │   └── loader.py
│   │   │   ├── infrastructure
│   │   │   │   ├── notifiers
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── router.py
│   │   │   │   │   ├── sms.py
│   │   │   │   │   └── windows_toast.py
│   │   │   │   └── stores.py
│   │   │   ├── services
│   │   │   │   ├── enrichment.py
│   │   │   │   ├── evaluation.py
│   │   │   │   └── orchestration.py
│   │   │   ├── __init__.py
│   │   │   ├── alert_controller.py
│   │   │   ├── alert_core_spec.md
│   │   │   ├── threshold_service.py
│   │   │   └── utils.py
│   │   ├── calc_core
│   │   │   ├── __init__.py
│   │   │   ├── calc_services.py
│   │   │   ├── calculation_core.py
│   │   │   ├── calculation_module_spec.md
│   │   │   └── calculation_services.py
│   │   ├── cyclone_core
│   │   │   ├── __init__.py
│   │   │   ├── cyclone_alert_service.py
│   │   │   ├── cyclone_bp.py
│   │   │   ├── cyclone_core_spec.md
│   │   │   ├── cyclone_engine.py
│   │   │   ├── cyclone_hedge_service.py
│   │   │   ├── cyclone_maintenance_service.py
│   │   │   ├── cyclone_portfolio_service.py
│   │   │   ├── cyclone_position_service.py
│   │   │   ├── cyclone_report_generator.py
│   │   │   └── cyclone_wallet_service.py
│   │   ├── hedge_core
│   │   │   ├── __init__.py
│   │   │   ├── auto_hedge_wizard.py
│   │   │   ├── hedge_calc_services.py
│   │   │   ├── hedge_calc_services_spec.md
│   │   │   ├── hedge_core.py
│   │   │   ├── hedge_core_module_spec.md
│   │   │   ├── hedge_services.py
│   │   │   └── hedge_wizard_bp.py
│   │   ├── monitor_core
│   │   │   ├── __init__.py
│   │   │   ├── base_monitor.py
│   │   │   ├── latency_monitor.py
│   │   │   ├── ledger_service.py
│   │   │   ├── monitor_api.py
│   │   │   ├── monitor_console.py
│   │   │   ├── monitor_core.py
│   │   │   ├── monitor_module_spec.md
│   │   │   ├── monitor_registry.py
│   │   │   ├── monitor_service.py
│   │   │   ├── monitor_utils.py
│   │   │   ├── operations_monitor.py
│   │   │   ├── position_monitor.py
│   │   │   ├── price_monitor.py
│   │   │   ├── profit_monitor.py
│   │   │   ├── profit_monitor_spec.md
│   │   │   ├── risk_monitor.py
│   │   │   ├── risk_monitor_spec.md
│   │   │   ├── sonic_monitor.py
│   │   │   ├── twilio_monitor.py
│   │   │   └── xcom_monitor.py
│   │   ├── oracle_core
│   │   │   ├── __init__.py
│   │   │   └── oracle_services.py
│   │   ├── positions_core
│   │   │   ├── __init__.py
│   │   │   ├── hedge_manager.py
│   │   │   ├── position_core.py
│   │   │   ├── position_core_detailed_spec.md
│   │   │   ├── position_core_service.py
│   │   │   ├── position_enrichment_service.py
│   │   │   ├── position_module_spec.md
│   │   │   ├── position_services.py
│   │   │   ├── position_store.py
│   │   │   └── position_sync_service.py
│   │   ├── wallet_core
│   │   │   ├── __init__.py
│   │   │   ├── encryption.py
│   │   │   ├── jupiter_api_spec.md
│   │   │   ├── wallet_controller.py
│   │   │   ├── wallet_core.py
│   │   │   ├── wallet_core_spec.md
│   │   │   ├── wallet_repository.py
│   │   │   ├── wallet_schema.py
│   │   │   └── wallet_service.py
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── core_imports.py
│   │   ├── locker_factory.py
│   │   └── logging.py
│   ├── data
│   │   ├── __init__.py
│   │   ├── data_locker.py
│   │   ├── database.py
│   │   ├── dl_alerts.py
│   │   ├── dl_hedges.py
│   │   ├── dl_modifiers.py
│   │   ├── dl_monitor_ledger.py
│   │   ├── dl_portfolio.py
│   │   ├── dl_positions.py
│   │   ├── dl_prices.py
│   │   ├── dl_system_data.py
│   │   ├── dl_traders.py
│   │   └── dl_wallets.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   ├── hedge.py
│   │   ├── portfolio.py
│   │   ├── position.py
│   │   └── wallet.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── cyclone_api.py
│   │   ├── portfolio_api.py
│   │   └── positions_api.py
│   ├── scripts
│   │   ├── create_virtual_env.py
│   │   ├── initialize_database.py
│   │   ├── insert_star_wars_traders.py
│   │   ├── insert_star_wars_wallets.py
│   │   ├── insert_wallets.py
│   │   ├── int_learning_db.py
│   │   ├── new_tree_protocol.py
│   │   ├── populate_learning_db.py
│   │   ├── recover_database.py
│   │   ├── seed_alert_thresholds.py
│   │   ├── scan_imports.py
│   │   ├── send_sms_demo.py
│   │   ├── setup_test_env.py
│   │   ├── twilio_run.py
│   │   ├── verify_all_tables_exist.py
│   │   ├── verify_position_schema.py
│   │   ├── verify_profit_alert.py
│   │   └── verify_risk_alert.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── database_service.py
│   │   ├── external_api_service.py
│   │   ├── position_service.py
│   │   └── xcom_service.py
│   ├── utils
│   │   ├── CONSOLE_LOGGER_SPEC.md
│   │   ├── __init__.py
│   │   ├── alert_helpers.py
│   │   ├── clear_caches.py
│   │   ├── console_logger.py
│   │   ├── db_retry.py
│   │   ├── fuzzy_wuzzy.py
│   │   ├── hedge_colors.py
│   │   ├── json_manager.py
│   │   ├── net_utils.py
│   │   ├── path_audit.py
│   │   ├── path_auto_fixer.py
│   │   ├── rich_logger.py
│   │   ├── route_decorators.py
│   │   ├── schema_validation_service.py
│   │   ├── startup_checker.py
│   │   ├── startup_service.py
│   │   ├── template_filters.py
│   │   ├── time_utils.py
│   │   ├── travel_percent_logger.py
│   │   └── update_ledger.py
│   ├── __init__.py
│   └── sonic_backend_app.py
├── docs
│   └── repo_map.md
├── frontend
│   ├── src
│   │   ├── api
│   │   │   ├── cyclone.js
│   │   │   ├── menu.js
│   │   │   └── products.js
│   │   ├── assets
│   │   │   ├── images
│   │   │   │   ├── auth
│   │   │   │   │   ├── auth-blue-card.svg
│   │   │   │   │   ├── auth-forgot-pass-multi-card.svg
│   │   │   │   │   ├── auth-mail-blue-card.svg
│   │   │   │   │   ├── auth-pattern-dark.svg
│   │   │   │   │   ├── auth-pattern.svg
│   │   │   │   │   ├── auth-purple-card.svg
│   │   │   │   │   ├── auth-reset-error-card.svg
│   │   │   │   │   ├── auth-reset-purple-card.svg
│   │   │   │   │   ├── auth-signup-blue-card.svg
│   │   │   │   │   ├── auth-signup-white-card.svg
│   │   │   │   │   ├── img-a2-checkmail.svg
│   │   │   │   │   ├── img-a2-codevarify.svg
│   │   │   │   │   ├── img-a2-forgotpass.svg
│   │   │   │   │   ├── img-a2-grid-dark.svg
│   │   │   │   │   ├── img-a2-grid.svg
│   │   │   │   │   ├── img-a2-login.svg
│   │   │   │   │   ├── img-a2-resetpass.svg
│   │   │   │   │   └── img-a2-signup.svg
│   │   │   │   ├── blog
│   │   │   │   │   ├── blog-1.png
│   │   │   │   │   ├── blog-2.png
│   │   │   │   │   ├── blog-3.png
│   │   │   │   │   ├── blog-4.png
│   │   │   │   │   ├── blog-5.png
│   │   │   │   │   ├── blog-6.png
│   │   │   │   │   ├── blog-7.png
│   │   │   │   │   ├── blog-8.png
│   │   │   │   │   ├── library-1.png
│   │   │   │   │   ├── library-2.png
│   │   │   │   │   ├── library-3.png
│   │   │   │   │   └── post-banner.png
│   │   │   │   ├── cards
│   │   │   │   │   ├── card-1.jpg
│   │   │   │   │   ├── card-2.jpg
│   │   │   │   │   └── card-3.jpg
│   │   │   │   ├── customization
│   │   │   │   │   ├── big.svg
│   │   │   │   │   ├── horizontal.svg
│   │   │   │   │   ├── ltr.svg
│   │   │   │   │   ├── max.svg
│   │   │   │   │   ├── mini.svg
│   │   │   │   │   ├── rtl.svg
│   │   │   │   │   ├── small.svg
│   │   │   │   │   └── vertical.svg
│   │   │   │   ├── e-commerce
│   │   │   │   │   ├── card.png
│   │   │   │   │   ├── cod.png
│   │   │   │   │   ├── completed.png
│   │   │   │   │   ├── discount.png
│   │   │   │   │   ├── empty-dark.svg
│   │   │   │   │   ├── empty.svg
│   │   │   │   │   ├── mastercard.png
│   │   │   │   │   ├── paypal.png
│   │   │   │   │   ├── prod-1.png
│   │   │   │   │   ├── prod-2.png
│   │   │   │   │   ├── prod-3.png
│   │   │   │   │   ├── prod-4.png
│   │   │   │   │   ├── prod-5.png
│   │   │   │   │   ├── prod-6.png
│   │   │   │   │   ├── prod-7.png
│   │   │   │   │   ├── prod-8.png
│   │   │   │   │   ├── prod-9.png
│   │   │   │   │   └── visa.png
│   │   │   │   ├── i18n
│   │   │   │   │   ├── china.svg
│   │   │   │   │   ├── france.svg
│   │   │   │   │   ├── romania.svg
│   │   │   │   │   └── united-states.svg
│   │   │   │   ├── icons
│   │   │   │   │   ├── auth0.svg
│   │   │   │   │   ├── aws.svg
│   │   │   │   │   ├── earning.svg
│   │   │   │   │   ├── facebook.svg
│   │   │   │   │   ├── firebase.svg
│   │   │   │   │   ├── google.svg
│   │   │   │   │   ├── jwt.svg
│   │   │   │   │   ├── linkedin.svg
│   │   │   │   │   ├── supabase.svg
│   │   │   │   │   └── twitter.svg
│   │   │   │   ├── landing
│   │   │   │   │   ├── frameworks
│   │   │   │   │   │   ├── angular.svg
│   │   │   │   │   │   ├── bootstrap.svg
│   │   │   │   │   │   ├── codeigniter.svg
│   │   │   │   │   │   ├── django.svg
│   │   │   │   │   │   ├── dot-net.svg
│   │   │   │   │   │   ├── flask.svg
│   │   │   │   │   │   ├── full-stack.svg
│   │   │   │   │   │   ├── shopify.svg
│   │   │   │   │   │   └── vue.svg
│   │   │   │   │   ├── offer
│   │   │   │   │   │   ├── offer-1.png
│   │   │   │   │   │   ├── offer-2.png
│   │   │   │   │   │   ├── offer-3.png
│   │   │   │   │   │   ├── offer-4.png
│   │   │   │   │   │   ├── offer-5.png
│   │   │   │   │   │   └── offer-6.png
│   │   │   │   │   ├── pre-apps
│   │   │   │   │   │   ├── slider-dark-1.png
│   │   │   │   │   │   ├── slider-dark-10.png
│   │   │   │   │   │   ├── slider-dark-11.png
│   │   │   │   │   │   ├── slider-dark-2.png
│   │   │   │   │   │   ├── slider-dark-3.png
│   │   │   │   │   │   ├── slider-dark-4.png
│   │   │   │   │   │   ├── slider-dark-5.png
│   │   │   │   │   │   ├── slider-dark-6.png
│   │   │   │   │   │   ├── slider-dark-7.png
│   │   │   │   │   │   ├── slider-dark-8.png
│   │   │   │   │   │   ├── slider-dark-9.png
│   │   │   │   │   │   ├── slider-light-1.png
│   │   │   │   │   │   ├── slider-light-10.png
│   │   │   │   │   │   ├── slider-light-11.png
│   │   │   │   │   │   ├── slider-light-2.png
│   │   │   │   │   │   ├── slider-light-3.png
│   │   │   │   │   │   ├── slider-light-4.png
│   │   │   │   │   │   ├── slider-light-5.png
│   │   │   │   │   │   ├── slider-light-6.png
│   │   │   │   │   │   ├── slider-light-7.png
│   │   │   │   │   │   ├── slider-light-8.png
│   │   │   │   │   │   └── slider-light-9.png
│   │   │   │   │   ├── bg-header.jpg
│   │   │   │   │   ├── bg-heand.png
│   │   │   │   │   ├── bg-hero-block-dark.png
│   │   │   │   │   ├── bg-hero-block-light.png
│   │   │   │   │   ├── bg-rtl-info-block-dark.png
│   │   │   │   │   ├── bg-rtl-info-block-light.png
│   │   │   │   │   ├── bg-rtl-info-dark.svg
│   │   │   │   │   ├── bg-rtl-info-light.svg
│   │   │   │   │   ├── customization-left.png
│   │   │   │   │   ├── customization-right.png
│   │   │   │   │   ├── footer-awards.png
│   │   │   │   │   ├── footer-dribble.png
│   │   │   │   │   ├── footer-freepik.png
│   │   │   │   │   ├── hero-dashboard.png
│   │   │   │   │   ├── hero-widget-1.png
│   │   │   │   │   ├── hero-widget-2.png
│   │   │   │   │   ├── tech-dark.svg
│   │   │   │   │   ├── tech-light.svg
│   │   │   │   │   └── widget-mail.svg
│   │   │   │   ├── maintenance
│   │   │   │   │   ├── 500-error.svg
│   │   │   │   │   ├── empty-dark.svg
│   │   │   │   │   ├── empty.svg
│   │   │   │   │   ├── img-bg-grid-dark.svg
│   │   │   │   │   ├── img-bg-grid.svg
│   │   │   │   │   ├── img-bg-parts.svg
│   │   │   │   │   ├── img-build.svg
│   │   │   │   │   ├── img-ct-dark-logo.png
│   │   │   │   │   ├── img-ct-light-logo.png
│   │   │   │   │   ├── img-error-bg-dark.svg
│   │   │   │   │   ├── img-error-bg.svg
│   │   │   │   │   ├── img-error-blue.svg
│   │   │   │   │   ├── img-error-purple.svg
│   │   │   │   │   ├── img-error-text.svg
│   │   │   │   │   ├── img-soon-2.svg
│   │   │   │   │   ├── img-soon-3.svg
│   │   │   │   │   ├── img-soon-4.svg
│   │   │   │   │   ├── img-soon-5.svg
│   │   │   │   │   ├── img-soon-6.svg
│   │   │   │   │   ├── img-soon-7.svg
│   │   │   │   │   ├── img-soon-8.svg
│   │   │   │   │   ├── img-soon-bg-grid-dark.svg
│   │   │   │   │   ├── img-soon-bg-grid.svg
│   │   │   │   │   ├── img-soon-bg.svg
│   │   │   │   │   ├── img-soon-block.svg
│   │   │   │   │   ├── img-soon-blue-block.svg
│   │   │   │   │   ├── img-soon-grid-dark.svg
│   │   │   │   │   ├── img-soon-grid.svg
│   │   │   │   │   └── img-soon-purple-block.svg
│   │   │   │   ├── pages
│   │   │   │   │   ├── card-discover.png
│   │   │   │   │   ├── card-master.png
│   │   │   │   │   ├── card-visa.png
│   │   │   │   │   ├── img-catalog1.png
│   │   │   │   │   ├── img-catalog2.png
│   │   │   │   │   └── img-catalog3.png
│   │   │   │   ├── profile
│   │   │   │   │   ├── img-gal-1.png
│   │   │   │   │   ├── img-gal-10.png
│   │   │   │   │   ├── img-gal-11.png
│   │   │   │   │   ├── img-gal-12.png
│   │   │   │   │   ├── img-gal-2.png
│   │   │   │   │   ├── img-gal-3.png
│   │   │   │   │   ├── img-gal-4.png
│   │   │   │   │   ├── img-gal-5.png
│   │   │   │   │   ├── img-gal-6.png
│   │   │   │   │   ├── img-gal-7.png
│   │   │   │   │   ├── img-gal-8.png
│   │   │   │   │   ├── img-gal-9.png
│   │   │   │   │   ├── img-profile-bg.png
│   │   │   │   │   ├── img-profile1.png
│   │   │   │   │   ├── img-profile2.jpg
│   │   │   │   │   ├── img-profile3.jpg
│   │   │   │   │   ├── profile-back-1.png
│   │   │   │   │   ├── profile-back-10.png
│   │   │   │   │   ├── profile-back-11.png
│   │   │   │   │   ├── profile-back-12.png
│   │   │   │   │   ├── profile-back-2.png
│   │   │   │   │   ├── profile-back-3.png
│   │   │   │   │   ├── profile-back-4.png
│   │   │   │   │   ├── profile-back-5.png
│   │   │   │   │   ├── profile-back-6.png
│   │   │   │   │   ├── profile-back-7.png
│   │   │   │   │   ├── profile-back-8.png
│   │   │   │   │   └── profile-back-9.png
│   │   │   │   ├── upload
│   │   │   │   │   └── upload.svg
│   │   │   │   ├── users
│   │   │   │   │   ├── avatar-1.png
│   │   │   │   │   ├── avatar-10.png
│   │   │   │   │   ├── avatar-11.png
│   │   │   │   │   ├── avatar-12.png
│   │   │   │   │   ├── avatar-2.png
│   │   │   │   │   ├── avatar-3.png
│   │   │   │   │   ├── avatar-4.png
│   │   │   │   │   ├── avatar-5.png
│   │   │   │   │   ├── avatar-6.png
│   │   │   │   │   ├── avatar-7.png
│   │   │   │   │   ├── avatar-8.png
│   │   │   │   │   ├── avatar-9.png
│   │   │   │   │   ├── img-user.png
│   │   │   │   │   ├── profile.png
│   │   │   │   │   └── user-round.svg
│   │   │   │   ├── widget
│   │   │   │   │   ├── australia.jpg
│   │   │   │   │   ├── brazil.jpg
│   │   │   │   │   ├── dashboard-1.jpg
│   │   │   │   │   ├── dashboard-2.jpg
│   │   │   │   │   ├── germany.jpg
│   │   │   │   │   ├── phone-1.jpg
│   │   │   │   │   ├── phone-2.jpg
│   │   │   │   │   ├── phone-3.jpg
│   │   │   │   │   ├── phone-4.jpg
│   │   │   │   │   ├── prod1.jpg
│   │   │   │   │   ├── prod2.jpg
│   │   │   │   │   ├── prod3.jpg
│   │   │   │   │   ├── prod4.jpg
│   │   │   │   │   ├── uk.jpg
│   │   │   │   │   └── usa.jpg
│   │   │   │   ├── logo-dark.svg
│   │   │   │   └── logo.svg
│   │   │   └── scss
│   │   │       ├── _theme1.module.scss
│   │   │       ├── _theme2.module.scss
│   │   │       ├── _theme3.module.scss
│   │   │       ├── _theme4.module.scss
│   │   │       ├── _theme5.module.scss
│   │   │       ├── _theme6.module.scss
│   │   │       ├── _themes-vars.module.scss
│   │   │       ├── scrollbar.scss
│   │   │       ├── style.scss
│   │   │       └── yet-another-react-lightbox.scss
│   │   ├── contexts
│   │   │   ├── AWSCognitoContext.jsx
│   │   │   ├── Auth0Context.jsx
│   │   │   ├── ConfigContext.jsx
│   │   │   ├── FirebaseContext.jsx
│   │   │   ├── JWTContext.jsx
│   │   │   └── SupabaseContext.jsx
│   │   ├── data
│   │   │   └── location.js
│   │   ├── hooks
│   │   │   ├── useAuth.js
│   │   │   ├── useConfig.js
│   │   │   ├── useDataGrid.js
│   │   │   ├── useLocalStorage.js
│   │   │   ├── useMenuCollapse.js
│   │   │   └── useScriptRef.js
│   │   ├── layout
│   │   │   ├── Customization
│   │   │   │   ├── BorderRadius.jsx
│   │   │   │   ├── BoxContainer.jsx
│   │   │   │   ├── FontFamily.jsx
│   │   │   │   ├── InputFilled.jsx
│   │   │   │   ├── Layout.jsx
│   │   │   │   ├── MenuOrientation.jsx
│   │   │   │   ├── PresetColor.jsx
│   │   │   │   ├── SidebarDrawer.jsx
│   │   │   │   ├── ThemeMode.jsx
│   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   ├── MainLayout
│   │   │   │   ├── Header
│   │   │   │   │   ├── CycloneRunSection
│   │   │   │   │   │   └── CycloneRunSection.jsx
│   │   │   │   │   ├── FullScreenSection
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── LocalizationSection
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── MegaMenuSection
│   │   │   │   │   │   ├── Banner.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── MobileSection
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── NotificationSection
│   │   │   │   │   │   ├── NotificationList.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ProfileSection
│   │   │   │   │   │   ├── UpgradePlanCard.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── SearchSection
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ThemeToggleSection
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── header.jsx
│   │   │   │   ├── LogoSection
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── MenuList
│   │   │   │   │   ├── NavCollapse
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── NavGroup
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── NavItem
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Sidebar
│   │   │   │   │   ├── MenuCard
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── MiniDrawerStyled.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Footer.jsx
│   │   │   │   ├── HorizontalBar.jsx
│   │   │   │   ├── MainContentStyled.js
│   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   ├── MinimalLayout
│   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   ├── SimpleLayout
│   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   ├── NavMotion.jsx
│   │   │   └── NavigationScroll.jsx
│   │   ├── menu-items
│   │   │   ├── application.js
│   │   │   ├── dashboard.js
│   │   │   ├── elements.js
│   │   │   ├── forms.js
│   │   │   ├── index.js
│   │   │   ├── other.js
│   │   │   ├── pages.js
│   │   │   ├── overview.js
│   │   │   ├── support.jsx
│   │   │   ├── utilities.js
│   │   │   └── widget.js
│   │   ├── metrics
│   │   │   ├── GTag.jsx
│   │   │   ├── MicrosoftClarity.jsx
│   │   │   ├── Notify.jsx
│   │   │   └── index_sonic_dashboard.jsx
│   │   ├── routes
│   │   │   ├── AuthenticationRoutes.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── LoginRoutes.jsx
│   │   │   ├── MainRoutes.jsx
│   │   │   ├── SimpleRoutes.jsx
│   │   │   └── index_sonic_dashboard.jsx
│   │   ├── store
│   │   │   ├── slices
│   │   │   │   ├── calendar.js
│   │   │   │   ├── cart.js
│   │   │   │   ├── chat.js
│   │   │   │   ├── contact.js
│   │   │   │   ├── customer.js
│   │   │   │   ├── kanban.js
│   │   │   │   ├── mail.js
│   │   │   │   ├── product.js
│   │   │   │   ├── snackbar.js
│   │   │   │   └── user.js
│   │   │   ├── accountReducer.js
│   │   │   ├── actions.js
│   │   │   ├── constant.js
│   │   │   ├── index.js
│   │   │   └── reducer.js
│   │   ├── themes
│   │   │   ├── overrides
│   │   │   │   ├── Chip.jsx
│   │   │   │   └── index.js
│   │   │   ├── compStyleOverride.jsx
│   │   │   ├── index_sonic_dashboard.jsx
│   │   │   ├── palette.jsx
│   │   │   ├── shadows.jsx
│   │   │   └── typography.jsx
│   │   ├── ui-component
│   │   │   ├── cards
│   │   │   │   ├── Blog
│   │   │   │   │   ├── Categories.jsx
│   │   │   │   │   ├── CommentCard.jsx
│   │   │   │   │   ├── CreateBlogCard.jsx
│   │   │   │   │   ├── DiscountCard.jsx
│   │   │   │   │   ├── Drafts.jsx
│   │   │   │   │   ├── HashtagsCard.jsx
│   │   │   │   │   ├── HeadingTab.jsx
│   │   │   │   │   ├── LikeCard.jsx
│   │   │   │   │   ├── SocialCard.jsx
│   │   │   │   │   ├── TopLikes.jsx
│   │   │   │   │   ├── TrendingArticles.jsx
│   │   │   │   │   └── VideoCard.jsx
│   │   │   │   ├── Post
│   │   │   │   │   ├── Comment
│   │   │   │   │   │   ├── Reply
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Skeleton
│   │   │   │   │   ├── EarningCard.jsx
│   │   │   │   │   ├── ImagePlaceholder.jsx
│   │   │   │   │   ├── PopularCard.jsx
│   │   │   │   │   ├── ProductPlaceholder.jsx
│   │   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   │   └── TotalIncomeCard.jsx
│   │   │   │   ├── AnalyticsChartCard.jsx
│   │   │   │   ├── AttachmentCard.jsx
│   │   │   │   ├── AuthFooter.jsx
│   │   │   │   ├── AuthSlider.jsx
│   │   │   │   ├── BackgroundPattern1.jsx
│   │   │   │   ├── BackgroundPattern2.jsx
│   │   │   │   ├── BillCard.jsx
│   │   │   │   ├── CardSecondaryAction.jsx
│   │   │   │   ├── ContactCard.jsx
│   │   │   │   ├── ContactList.jsx
│   │   │   │   ├── FloatingCart.jsx
│   │   │   │   ├── FollowerCard.jsx
│   │   │   │   ├── FriendRequestCard.jsx
│   │   │   │   ├── FriendsCard.jsx
│   │   │   │   ├── GalleryCard.jsx
│   │   │   │   ├── HoverDataCard.jsx
│   │   │   │   ├── HoverSocialCard.jsx
│   │   │   │   ├── IconNumberCard.jsx
│   │   │   │   ├── MainCard.jsx
│   │   │   │   ├── ProductCard.jsx
│   │   │   │   ├── ProductReview.jsx
│   │   │   │   ├── ReportCard.jsx
│   │   │   │   ├── RevenueCard.jsx
│   │   │   │   ├── RoundIconCard.jsx
│   │   │   │   ├── SalesLineChartCard.jsx
│   │   │   │   ├── SeoChartCard.jsx
│   │   │   │   ├── SideIconCard.jsx
│   │   │   │   ├── SubCard.jsx
│   │   │   │   ├── TotalIncomeDarkCard.jsx
│   │   │   │   ├── TotalIncomeLightCard.jsx
│   │   │   │   ├── TotalLeverageDarkCard.jsx
│   │   │   │   ├── TotalLeverageLightCard.jsx
│   │   │   │   ├── TotalLineChartCard.jsx
│   │   │   │   ├── TotalSizeDarkCard.jsx
│   │   │   │   ├── TotalSizeLightCard.jsx
│   │   │   │   ├── TotalValueCard.jsx
│   │   │   │   ├── UserCountCard.jsx
│   │   │   │   ├── UserDetailsCard.jsx
│   │   │   │   ├── UserProfileCard.jsx
│   │   │   │   └── UserSimpleCard.jsx
│   │   │   ├── extended
│   │   │   │   ├── Form
│   │   │   │   │   ├── FormControl.jsx
│   │   │   │   │   ├── FormControlSelect.jsx
│   │   │   │   │   └── InputLabel.jsx
│   │   │   │   ├── notistack
│   │   │   │   │   ├── ColorVariants.jsx
│   │   │   │   │   ├── CustomComponent.jsx
│   │   │   │   │   ├── Dense.jsx
│   │   │   │   │   ├── DismissSnackBar.jsx
│   │   │   │   │   ├── HideDuration.jsx
│   │   │   │   │   ├── IconVariants.jsx
│   │   │   │   │   ├── MaxSnackbar.jsx
│   │   │   │   │   ├── PositioningSnackbar.jsx
│   │   │   │   │   ├── PreventDuplicate.jsx
│   │   │   │   │   ├── SnackBarAction.jsx
│   │   │   │   │   ├── TransitionBar.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Accordion.jsx
│   │   │   │   ├── AnimateButton.jsx
│   │   │   │   ├── AppBar.jsx
│   │   │   │   ├── Avatar.jsx
│   │   │   │   ├── Breadcrumbs.jsx
│   │   │   │   ├── ImageList.jsx
│   │   │   │   ├── Snackbar.jsx
│   │   │   │   └── Transitions.jsx
│   │   │   ├── third-party
│   │   │   │   ├── dropzone
│   │   │   │   │   ├── Avatar.jsx
│   │   │   │   │   ├── FilePreview.jsx
│   │   │   │   │   ├── MultiFile.jsx
│   │   │   │   │   ├── PlaceHolderContent.jsx
│   │   │   │   │   ├── RejectionFile.jsx
│   │   │   │   │   └── SingleFile.jsx
│   │   │   │   ├── map
│   │   │   │   │   ├── ControlPanelStyled.jsx
│   │   │   │   │   ├── MapContainerStyled.jsx
│   │   │   │   │   ├── MapControl.jsx
│   │   │   │   │   ├── MapControlsStyled.jsx
│   │   │   │   │   ├── MapMarker.jsx
│   │   │   │   │   ├── MapPopup.jsx
│   │   │   │   │   └── PopupStyled.jsx
│   │   │   │   ├── Notistack.jsx
│   │   │   │   └── ReactQuill.jsx
│   │   │   ├── Loadable.jsx
│   │   │   ├── Loader.jsx
│   │   │   ├── Locales.jsx
│   │   │   ├── Logo.jsx
│   │   │   └── RTLLayout.jsx
│   │   ├── utils
│   │   │   ├── locales
│   │   │   │   ├── en.json
│   │   │   │   ├── fr.json
│   │   │   │   ├── ro.json
│   │   │   │   └── zh.json
│   │   │   ├── route-guard
│   │   │   │   ├── AuthGuard.jsx
│   │   │   │   └── GuestGuard.jsx
│   │   │   ├── axios.js
│   │   │   ├── getDropzoneData.js
│   │   │   ├── getImageUrl.js
│   │   │   └── password-strength.js
│   │   ├── views
│   │   │   ├── application
│   │   │   │   ├── blog
│   │   │   │   │   ├── AddNewBlog
│   │   │   │   │   │   ├── AddNewForm.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Dashboard
│   │   │   │   │   │   ├── AnalyticsBarChart.jsx
│   │   │   │   │   │   ├── RecentBlogList.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Details
│   │   │   │   │   │   ├── BlogCommonCard.jsx
│   │   │   │   │   │   ├── BlogDetailsCard.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── EditBlog
│   │   │   │   │   │   ├── EditForm.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── GeneralSettings
│   │   │   │   │   │   ├── Articles.jsx
│   │   │   │   │   │   ├── Drafts.jsx
│   │   │   │   │   │   ├── GeneralSetting.jsx
│   │   │   │   │   │   ├── YourLibrary.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── List
│   │   │   │   │   │   ├── BlogCommonCard.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── chart-data
│   │   │   │   │   │   └── analytics-bar-charts.jsx
│   │   │   │   │   └── data
│   │   │   │   │       └── index.js
│   │   │   │   ├── calendar
│   │   │   │   │   ├── AddEventForm.jsx
│   │   │   │   │   ├── CalendarStyled.jsx
│   │   │   │   │   ├── ColorPalette.jsx
│   │   │   │   │   ├── Toolbar.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── chat
│   │   │   │   │   ├── AvatarStatus.jsx
│   │   │   │   │   ├── ChartHistory.jsx
│   │   │   │   │   ├── ChatDrawer.jsx
│   │   │   │   │   ├── UserAvatar.jsx
│   │   │   │   │   ├── UserDetails.jsx
│   │   │   │   │   ├── UserList.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── contact
│   │   │   │   │   ├── Card
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── List
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UserDetails.jsx
│   │   │   │   │   └── UserEdit.jsx
│   │   │   │   ├── crm
│   │   │   │   │   ├── ContactManagement
│   │   │   │   │   │   ├── CommunicationHistory
│   │   │   │   │   │   │   ├── Filter.jsx
│   │   │   │   │   │   │   ├── HistoryTableBody.jsx
│   │   │   │   │   │   │   ├── HistoryTableHeader.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── ContactCard
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── ContactList
│   │   │   │   │   │   │   ├── AddContactDialog.jsx
│   │   │   │   │   │   │   ├── AddContactDialogContent.jsx
│   │   │   │   │   │   │   ├── ContactTableBody.jsx
│   │   │   │   │   │   │   ├── ContactTableHeader.jsx
│   │   │   │   │   │   │   ├── Filter.jsx
│   │   │   │   │   │   │   ├── NewMessage.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── RemindersFollowUp
│   │   │   │   │   │       ├── Filter.jsx
│   │   │   │   │   │       ├── FollowupTableBody.jsx
│   │   │   │   │   │       ├── FollowupTableHeader.jsx
│   │   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── LeadManagement
│   │   │   │   │   │   ├── LeadList
│   │   │   │   │   │   │   ├── AddLeadDialog.jsx
│   │   │   │   │   │   │   ├── AddLeadDialogBody.jsx
│   │   │   │   │   │   │   ├── Filter.jsx
│   │   │   │   │   │   │   ├── FilterLeadList.jsx
│   │   │   │   │   │   │   ├── LeadDrawer.jsx
│   │   │   │   │   │   │   ├── LeadTable.jsx
│   │   │   │   │   │   │   ├── LeadTableBody.jsx
│   │   │   │   │   │   │   ├── LeadTableHeader.jsx
│   │   │   │   │   │   │   ├── NewMessage.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── Overview
│   │   │   │   │   │       ├── LeadCards.jsx
│   │   │   │   │   │       ├── LeadSource.jsx
│   │   │   │   │   │       ├── LeadSummary.jsx
│   │   │   │   │   │       ├── SalesPerformance.jsx
│   │   │   │   │   │       ├── UpcomingTask.jsx
│   │   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   │   └── SalesManagement
│   │   │   │   │       ├── Earning
│   │   │   │   │       │   ├── EarningHeader.jsx
│   │   │   │   │       │   ├── EarningTable.jsx
│   │   │   │   │       │   ├── Filter.jsx
│   │   │   │   │       │   ├── Overview.jsx
│   │   │   │   │       │   └── index_sonic_dashboard.jsx
│   │   │   │   │       ├── Refund
│   │   │   │   │       │   ├── Filter.jsx
│   │   │   │   │       │   ├── Overview.jsx
│   │   │   │   │       │   ├── RefundHeader.jsx
│   │   │   │   │       │   ├── RefundTable.jsx
│   │   │   │   │       │   └── index_sonic_dashboard.jsx
│   │   │   │   │       └── Statement
│   │   │   │   │           ├── Filter.jsx
│   │   │   │   │           ├── OverView.jsx
│   │   │   │   │           ├── StatementHeader.jsx
│   │   │   │   │           ├── StatementTable.jsx
│   │   │   │   │           └── index_sonic_dashboard.jsx
│   │   │   │   ├── customer
│   │   │   │   │   ├── CreateInvoice
│   │   │   │   │   │   ├── AddItemPage.jsx
│   │   │   │   │   │   ├── ProductsPage.jsx
│   │   │   │   │   │   ├── TotalCard.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── OrderDetails
│   │   │   │   │   │   ├── Details.jsx
│   │   │   │   │   │   ├── Invoice.jsx
│   │   │   │   │   │   ├── Status.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Product
│   │   │   │   │   │   ├── ProductAdd.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ProductReview
│   │   │   │   │   │   ├── ReviewEdit.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── CustomerList.jsx
│   │   │   │   │   └── OrderList.jsx
│   │   │   │   ├── e-commerce
│   │   │   │   │   ├── Checkout
│   │   │   │   │   │   ├── AddAddress.jsx
│   │   │   │   │   │   ├── AddPaymentCard.jsx
│   │   │   │   │   │   ├── AddressCard.jsx
│   │   │   │   │   │   ├── BillingAddress.jsx
│   │   │   │   │   │   ├── Cart.jsx
│   │   │   │   │   │   ├── CartDiscount.jsx
│   │   │   │   │   │   ├── CartEmpty.jsx
│   │   │   │   │   │   ├── CouponCode.jsx
│   │   │   │   │   │   ├── OrderComplete.jsx
│   │   │   │   │   │   ├── OrderSummary.jsx
│   │   │   │   │   │   ├── Payment.jsx
│   │   │   │   │   │   ├── PaymentCard.jsx
│   │   │   │   │   │   ├── PaymentOptions.js
│   │   │   │   │   │   ├── PaymentSelect.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ProductDetails
│   │   │   │   │   │   ├── ProductDescription.jsx
│   │   │   │   │   │   ├── ProductImages.jsx
│   │   │   │   │   │   ├── ProductInfo.jsx
│   │   │   │   │   │   ├── ProductReview.jsx
│   │   │   │   │   │   ├── RelatedProducts.jsx
│   │   │   │   │   │   ├── Specification.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Products
│   │   │   │   │   │   ├── Colors.jsx
│   │   │   │   │   │   ├── ProductEmpty.jsx
│   │   │   │   │   │   ├── ProductFilter.jsx
│   │   │   │   │   │   ├── ProductFilterView.jsx
│   │   │   │   │   │   ├── SortOptions.js
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ColorOptions.js
│   │   │   │   │   └── ProductList.jsx
│   │   │   │   ├── invoice
│   │   │   │   │   ├── Client
│   │   │   │   │   │   ├── AddClient
│   │   │   │   │   │   │   ├── Address.jsx
│   │   │   │   │   │   │   ├── ContactDetail.jsx
│   │   │   │   │   │   │   ├── OtherDetail.jsx
│   │   │   │   │   │   │   ├── PersonalInformation.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── ClientList
│   │   │   │   │   │       ├── ClientDetails.jsx
│   │   │   │   │   │       ├── ClientDrawer.jsx
│   │   │   │   │   │       ├── ClientFilter.jsx
│   │   │   │   │   │       ├── ClientTable.jsx
│   │   │   │   │   │       ├── ClientTableHeader.jsx
│   │   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Create
│   │   │   │   │   │   ├── AmountCard.jsx
│   │   │   │   │   │   ├── ClientInfo.jsx
│   │   │   │   │   │   ├── ItemList.jsx
│   │   │   │   │   │   ├── SelectItem.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Dashboard
│   │   │   │   │   │   ├── ClientInsights.jsx
│   │   │   │   │   │   ├── QuickAdd.jsx
│   │   │   │   │   │   ├── RecentActivity.jsx
│   │   │   │   │   │   ├── RevenueBarChart.jsx
│   │   │   │   │   │   ├── SupportHelp.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Details
│   │   │   │   │   │   ├── DetailsTab.jsx
│   │   │   │   │   │   ├── InvoiceTab.jsx
│   │   │   │   │   │   ├── StatusTab.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Edit
│   │   │   │   │   │   ├── AmountCard.jsx
│   │   │   │   │   │   ├── ClientInfo.jsx
│   │   │   │   │   │   ├── ItemList.jsx
│   │   │   │   │   │   ├── SelectItem.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Items
│   │   │   │   │   │   ├── ItemList
│   │   │   │   │   │   │   ├── ItemDetails.jsx
│   │   │   │   │   │   │   ├── ItemDrawer.jsx
│   │   │   │   │   │   │   ├── ItemFilter.jsx
│   │   │   │   │   │   │   ├── ItemTable.jsx
│   │   │   │   │   │   │   ├── ItemTableHeader.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── AddItem.jsx
│   │   │   │   │   ├── List
│   │   │   │   │   │   ├── InvoiceFilter.jsx
│   │   │   │   │   │   ├── InvoiceTable.jsx
│   │   │   │   │   │   ├── InvoiceTableHeader.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Payment
│   │   │   │   │   │   ├── AddPayment
│   │   │   │   │   │   │   ├── PaymentTable.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── PaymentDetails
│   │   │   │   │   │   │   ├── PaymentTable.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── PaymentList
│   │   │   │   │   │       ├── Overview.jsx
│   │   │   │   │   │       ├── PaymentFilter.jsx
│   │   │   │   │   │       ├── PaymentTable.jsx
│   │   │   │   │   │       ├── PaymentTableHeader.jsx
│   │   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   │   └── chart-data
│   │   │   │   │       ├── index_sonic_dashboard.jsx
│   │   │   │   │       ├── invoice-chart-1.jsx
│   │   │   │   │       ├── invoice-chart-2.jsx
│   │   │   │   │       ├── invoice-chart-3.jsx
│   │   │   │   │       ├── invoice-chart-4.jsx
│   │   │   │   │       └── revenue-bar-chart.jsx
│   │   │   │   ├── kanban
│   │   │   │   │   ├── Backlogs
│   │   │   │   │   │   ├── AddItem.jsx
│   │   │   │   │   │   ├── AddStory.jsx
│   │   │   │   │   │   ├── AddStoryComment.jsx
│   │   │   │   │   │   ├── AlertStoryDelete.jsx
│   │   │   │   │   │   ├── EditStory.jsx
│   │   │   │   │   │   ├── Items.jsx
│   │   │   │   │   │   ├── StoryComment.jsx
│   │   │   │   │   │   ├── UserStory.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Board
│   │   │   │   │   │   ├── AddColumn.jsx
│   │   │   │   │   │   ├── AddItem.jsx
│   │   │   │   │   │   ├── AddItemComment.jsx
│   │   │   │   │   │   ├── AlertColumnDelete.jsx
│   │   │   │   │   │   ├── AlertItemDelete.jsx
│   │   │   │   │   │   ├── Columns.jsx
│   │   │   │   │   │   ├── EditColumn.jsx
│   │   │   │   │   │   ├── EditItem.jsx
│   │   │   │   │   │   ├── ItemComment.jsx
│   │   │   │   │   │   ├── ItemDetails.jsx
│   │   │   │   │   │   ├── Items.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── mail
│   │   │   │   │   ├── ComposeDialog.jsx
│   │   │   │   │   ├── MailDetails.jsx
│   │   │   │   │   ├── MailDrawer.jsx
│   │   │   │   │   ├── MailEmpty.jsx
│   │   │   │   │   ├── MailList.jsx
│   │   │   │   │   ├── MailListHeader.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── map
│   │   │   │   │   ├── maps
│   │   │   │   │   │   ├── change-theme
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── clusters-map
│   │   │   │   │   │   │   ├── index_sonic_dashboard.jsx
│   │   │   │   │   │   │   └── layers.js
│   │   │   │   │   │   ├── draggable-marker
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── heatmap
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   ├── index_sonic_dashboard.jsx
│   │   │   │   │   │   │   └── map-style.js
│   │   │   │   │   │   ├── interaction-map
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── side-by-side
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── viewport-animation
│   │   │   │   │   │   │   ├── control-panel.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   ├── GeoJSONAnimation.jsx
│   │   │   │   │   │   ├── HighlightByFilter.jsx
│   │   │   │   │   │   └── MarkersPopups.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   └── users
│   │   │   │       ├── account-profile
│   │   │   │       │   ├── Profile1
│   │   │   │       │   │   ├── ChangePassword.jsx
│   │   │   │       │   │   ├── MyAccount.jsx
│   │   │   │       │   │   ├── PersonalAccount.jsx
│   │   │   │       │   │   ├── Profile.jsx
│   │   │   │       │   │   ├── Settings.jsx
│   │   │   │       │   │   └── index_sonic_dashboard.jsx
│   │   │   │       │   ├── Profile2
│   │   │   │       │   │   ├── Billing.jsx
│   │   │   │       │   │   ├── ChangePassword.jsx
│   │   │   │       │   │   ├── Payment.jsx
│   │   │   │       │   │   ├── UserProfile.jsx
│   │   │   │       │   │   └── index_sonic_dashboard.jsx
│   │   │   │       │   └── Profile3
│   │   │   │       │       ├── Billing.jsx
│   │   │   │       │       ├── Notifications.jsx
│   │   │   │       │       ├── Profile.jsx
│   │   │   │       │       ├── Security.jsx
│   │   │   │       │       └── index_sonic_dashboard.jsx
│   │   │   │       ├── card
│   │   │   │       │   ├── CardStyle1.jsx
│   │   │   │       │   ├── CardStyle2.jsx
│   │   │   │       │   └── CardStyle3.jsx
│   │   │   │       ├── list
│   │   │   │       │   ├── Style1
│   │   │   │       │   │   ├── UserList.jsx
│   │   │   │       │   │   └── index_sonic_dashboard.jsx
│   │   │   │       │   └── Style2
│   │   │   │       │       ├── UserList.jsx
│   │   │   │       │       └── index_sonic_dashboard.jsx
│   │   │   │       └── social-profile
│   │   │   │           ├── Followers.jsx
│   │   │   │           ├── FriendRequest.jsx
│   │   │   │           ├── Friends.jsx
│   │   │   │           ├── Gallery.jsx
│   │   │   │           ├── Profile.jsx
│   │   │   │           └── index_sonic_dashboard.jsx
│   │   │   ├── cyclone
│   │   │   │   └── Run.jsx
│   │   │   ├── dashboard
│   │   │   │   ├── Analytics
│   │   │   │   │   ├── chart-data
│   │   │   │   │   │   └── market-share-area-chart.jsx
│   │   │   │   │   ├── PositionListCard.jsx
│   │   │   │   │   ├── PerformanceGraphCard.jsx
│   │   │   │   │   ├── TraderListCard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Default
│   │   │   │   │   ├── chart-data
│   │   │   │   │   │   ├── bajaj-area-chart.jsx
│   │   │   │   │   │   ├── total-growth-bar-chart.jsx
│   │   │   │   │   │   ├── total-order-month-line-chart.jsx
│   │   │   │   │   │   └── total-order-year-line-chart.jsx
│   │   │   │   │   ├── BajajAreaChartCard.jsx
│   │   │   │   │   ├── EarningCard.jsx
│   │   │   │   │   ├── PopularCard.jsx
│   │   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   │   ├── TotalOrderLineChartCard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   └── Sonic
│   │   │   │       ├── chart-data
│   │   │   │       │   └── market-share-area-chart.jsx
│   │   │   │       ├── PositionListCard.jsx
│   │   │   │       ├── PositionTableCard.jsx
│   │   │   │       ├── SizeHedgeChartCard.jsx
│   │   │   │       ├── TraderListCard.jsx
│   │   │   │       ├── ValueToCollateralChartCard.jsx
│   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   ├── forms
│   │   │   │   ├── chart
│   │   │   │   │   ├── Apexchart
│   │   │   │   │   │   ├── ApexAreaChart.jsx
│   │   │   │   │   │   ├── ApexBarChart.jsx
│   │   │   │   │   │   ├── ApexColumnChart.jsx
│   │   │   │   │   │   ├── ApexLineChart.jsx
│   │   │   │   │   │   ├── ApexMixedChart.jsx
│   │   │   │   │   │   ├── ApexPieChart.jsx
│   │   │   │   │   │   ├── ApexPolarChart.jsx
│   │   │   │   │   │   ├── ApexRedialChart.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── OrgChart
│   │   │   │   │       ├── Card.jsx
│   │   │   │   │       ├── DataCard.jsx
│   │   │   │   │       ├── LinkedIn.jsx
│   │   │   │   │       ├── MeetIcon.jsx
│   │   │   │   │       ├── SkypeIcon.jsx
│   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   ├── components
│   │   │   │   │   ├── DateTime
│   │   │   │   │   │   ├── CustomDateTime.jsx
│   │   │   │   │   │   ├── LandscapeDateTime.jsx
│   │   │   │   │   │   ├── ViewRendererDateTime.jsx
│   │   │   │   │   │   ├── ViewsDateTimePicker.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── Slider
│   │   │   │   │   │   ├── BasicSlider.jsx
│   │   │   │   │   │   ├── DisableSlider.jsx
│   │   │   │   │   │   ├── LabelSlider.jsx
│   │   │   │   │   │   ├── PopupSlider.jsx
│   │   │   │   │   │   ├── StepSlider.jsx
│   │   │   │   │   │   ├── VerticalSlider.jsx
│   │   │   │   │   │   ├── VolumeSlider.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── AutoComplete.jsx
│   │   │   │   │   ├── Button.jsx
│   │   │   │   │   ├── Checkbox.jsx
│   │   │   │   │   ├── Radio.jsx
│   │   │   │   │   ├── Switch.jsx
│   │   │   │   │   └── TextField.jsx
│   │   │   │   ├── data-grid
│   │   │   │   │   ├── ColumnGroups
│   │   │   │   │   │   ├── BasicColumnGroup.jsx
│   │   │   │   │   │   ├── CustomColumnGroup.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ColumnMenu
│   │   │   │   │   │   ├── AddMenuItem.jsx
│   │   │   │   │   │   ├── ColumnMenu.jsx
│   │   │   │   │   │   ├── CustomMenu.jsx
│   │   │   │   │   │   ├── DisableMenu.jsx
│   │   │   │   │   │   ├── HideMenuItem.jsx
│   │   │   │   │   │   ├── OverrideMenu.jsx
│   │   │   │   │   │   ├── ReorderingMenu.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ColumnVirtualization
│   │   │   │   │   │   ├── Virtualization.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ColumnVisibility
│   │   │   │   │   │   ├── ControlledVisibility.jsx
│   │   │   │   │   │   ├── InitializeColumnVisibility.jsx
│   │   │   │   │   │   ├── VisibilityPanel.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── DataGridBasic
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── InLineEditing
│   │   │   │   │   │   ├── AutoStop.jsx
│   │   │   │   │   │   ├── ConfirmationSave.jsx
│   │   │   │   │   │   ├── Controlled.jsx
│   │   │   │   │   │   ├── CustomEdit.jsx
│   │   │   │   │   │   ├── DisableEditing.jsx
│   │   │   │   │   │   ├── EditableColumn.jsx
│   │   │   │   │   │   ├── EditableRow.jsx
│   │   │   │   │   │   ├── EditingEvents.jsx
│   │   │   │   │   │   ├── FullFeatured.jsx
│   │   │   │   │   │   ├── ParserSetter.jsx
│   │   │   │   │   │   ├── ServerValidation.jsx
│   │   │   │   │   │   ├── Validation.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── QuickFilter
│   │   │   │   │   │   ├── CustomFilter.jsx
│   │   │   │   │   │   ├── ExcludeHiddenColumns.jsx
│   │   │   │   │   │   ├── Initialize.jsx
│   │   │   │   │   │   ├── ParsingValues.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── SaveRestoreState
│   │   │   │   │       ├── InitialState.jsx
│   │   │   │   │       ├── UseGridSelector.jsx
│   │   │   │   │       └── index_sonic_dashboard.jsx
│   │   │   │   ├── forms-validation
│   │   │   │   │   ├── AutocompleteForms.jsx
│   │   │   │   │   ├── CheckboxForms.jsx
│   │   │   │   │   ├── InstantFeedback.jsx
│   │   │   │   │   ├── LoginForms.jsx
│   │   │   │   │   ├── RadioGroupForms.jsx
│   │   │   │   │   ├── SelectForms.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── forms-wizard
│   │   │   │   │   ├── BasicWizard
│   │   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   │   ├── Review.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── ValidationWizard
│   │   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   │   ├── Review.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── layouts
│   │   │   │   │   ├── ActionBar.jsx
│   │   │   │   │   ├── Layouts.jsx
│   │   │   │   │   ├── MultiColumnForms.jsx
│   │   │   │   │   └── StickyActionBar.jsx
│   │   │   │   ├── plugins
│   │   │   │   │   ├── Modal
│   │   │   │   │   │   ├── ServerModal.jsx
│   │   │   │   │   │   ├── SimpleModal.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── AutoComplete.jsx
│   │   │   │   │   ├── Clipboard.jsx
│   │   │   │   │   ├── Dropzone.jsx
│   │   │   │   │   ├── Editor.jsx
│   │   │   │   │   ├── Mask.jsx
│   │   │   │   │   ├── Recaptcha.jsx
│   │   │   │   │   └── Tooltip.jsx
│   │   │   │   └── tables
│   │   │   │       ├── TableBasic.jsx
│   │   │   │       ├── TableCollapsible.jsx
│   │   │   │       ├── TableData.jsx
│   │   │   │       ├── TableDense.jsx
│   │   │   │       ├── TableEnhanced.jsx
│   │   │   │       ├── TableExports.jsx
│   │   │   │       ├── TableStickyHead.jsx
│   │   │   │       └── TablesCustomized.jsx
│   │   │   ├── pages
│   │   │   │   ├── authentication
│   │   │   │   │   ├── auth0
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── authentication1
│   │   │   │   │   │   ├── CheckMail1.jsx
│   │   │   │   │   │   ├── CodeVerification1.jsx
│   │   │   │   │   │   ├── ForgotPassword1.jsx
│   │   │   │   │   │   ├── Login1.jsx
│   │   │   │   │   │   ├── Register1.jsx
│   │   │   │   │   │   └── ResetPassword1.jsx
│   │   │   │   │   ├── authentication2
│   │   │   │   │   │   ├── CheckMail2.jsx
│   │   │   │   │   │   ├── CodeVerification2.jsx
│   │   │   │   │   │   ├── ForgotPassword2.jsx
│   │   │   │   │   │   ├── Login2.jsx
│   │   │   │   │   │   ├── Register2.jsx
│   │   │   │   │   │   └── ResetPassword2.jsx
│   │   │   │   │   ├── aws
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── firebase
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   ├── AuthResetPassword.jsx
│   │   │   │   │   │   └── FirebaseSocial.jsx
│   │   │   │   │   ├── jwt
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── supabase
│   │   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   │   ├── AuthCardWrapper.jsx
│   │   │   │   │   ├── AuthWrapper1.jsx
│   │   │   │   │   ├── AuthWrapper2.jsx
│   │   │   │   │   ├── CheckMail.jsx
│   │   │   │   │   ├── CodeVerification.jsx
│   │   │   │   │   ├── ForgotPassword.jsx
│   │   │   │   │   ├── Login.jsx
│   │   │   │   │   ├── LoginProvider.jsx
│   │   │   │   │   ├── Register.jsx
│   │   │   │   │   ├── ResetPassword.jsx
│   │   │   │   │   └── ViewOnlyAlert.jsx
│   │   │   │   ├── contact-us
│   │   │   │   │   ├── ContactCard.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── landing
│   │   │   │   │   ├── Animation.jsx
│   │   │   │   │   ├── CardData.js
│   │   │   │   │   ├── CardSection.jsx
│   │   │   │   │   ├── CustomizeSection.jsx
│   │   │   │   │   ├── FeatureSection.jsx
│   │   │   │   │   ├── FooterSection.jsx
│   │   │   │   │   ├── FrameworkSection.jsx
│   │   │   │   │   ├── HeaderSection.jsx
│   │   │   │   │   ├── IncludeSection.jsx
│   │   │   │   │   ├── PeopleCard.jsx
│   │   │   │   │   ├── PeopleSection.jsx
│   │   │   │   │   ├── PreBuildDashBoard.jsx
│   │   │   │   │   ├── RtlInfoSection.jsx
│   │   │   │   │   ├── StartupProjectSection.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── maintenance
│   │   │   │   │   ├── ComingSoon
│   │   │   │   │   │   ├── ComingSoon1
│   │   │   │   │   │   │   ├── MailerSubscriber.jsx
│   │   │   │   │   │   │   ├── Slider.jsx
│   │   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   │   └── ComingSoon2.jsx
│   │   │   │   │   ├── Error.jsx
│   │   │   │   │   ├── Error500.jsx
│   │   │   │   │   └── UnderConstruction.jsx
│   │   │   │   ├── pricing
│   │   │   │   │   ├── Price1.jsx
│   │   │   │   │   └── Price2.jsx
│   │   │   │   └── saas-pages
│   │   │   │       ├── Faqs.jsx
│   │   │   │       └── PrivacyPolicy.jsx
│   │   │   ├── overview
│   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   ├── ui-elements
│   │   │   │   ├── advance
│   │   │   │   │   ├── UIDialog
│   │   │   │   │   │   ├── AlertDialog.jsx
│   │   │   │   │   │   ├── AlertDialogSlide.jsx
│   │   │   │   │   │   ├── ConfirmationDialog.jsx
│   │   │   │   │   │   ├── CustomizedDialogs.jsx
│   │   │   │   │   │   ├── DraggableDialog.jsx
│   │   │   │   │   │   ├── FormDialog.jsx
│   │   │   │   │   │   ├── FullScreenDialog.jsx
│   │   │   │   │   │   ├── MaxWidthDialog.jsx
│   │   │   │   │   │   ├── ResponsiveDialog.jsx
│   │   │   │   │   │   ├── ScrollDialog.jsx
│   │   │   │   │   │   ├── SimpleDialog.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UIRating
│   │   │   │   │   │   ├── CustomizedRatings.jsx
│   │   │   │   │   │   ├── HalfRating.jsx
│   │   │   │   │   │   ├── HoverRating.jsx
│   │   │   │   │   │   ├── SimpleRating.jsx
│   │   │   │   │   │   ├── SizeRating.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UISpeeddial
│   │   │   │   │   │   ├── OpenIconSpeedDial.jsx
│   │   │   │   │   │   ├── SimpleSpeedDials.jsx
│   │   │   │   │   │   ├── SpeedDialTooltipOpen.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UITimeline
│   │   │   │   │   │   ├── AlternateTimeline.jsx
│   │   │   │   │   │   ├── BasicTimeline.jsx
│   │   │   │   │   │   ├── ColorsTimeline.jsx
│   │   │   │   │   │   ├── CustomizedTimeline.jsx
│   │   │   │   │   │   ├── OppositeContentTimeline.jsx
│   │   │   │   │   │   ├── OutlinedTimeline.jsx
│   │   │   │   │   │   ├── RightAlignedTimeline.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UIToggleButton
│   │   │   │   │   │   ├── CustomizedDividers.jsx
│   │   │   │   │   │   ├── ExclusiveToggleButtons.jsx
│   │   │   │   │   │   ├── StandaloneToggleButton.jsx
│   │   │   │   │   │   ├── ToggleButtonNotEmpty.jsx
│   │   │   │   │   │   ├── ToggleButtonSizes.jsx
│   │   │   │   │   │   ├── ToggleButtonsMultiple.jsx
│   │   │   │   │   │   ├── VerticalToggleButtons.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UITreeview
│   │   │   │   │   │   ├── ControlledTreeView.jsx
│   │   │   │   │   │   ├── CustomizedTreeView.jsx
│   │   │   │   │   │   ├── FileSystemNavigator.jsx
│   │   │   │   │   │   ├── GmailTreeView.jsx
│   │   │   │   │   │   ├── MultiSelectTreeView.jsx
│   │   │   │   │   │   ├── RecursiveTreeView.jsx
│   │   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   │   ├── UIAlert.jsx
│   │   │   │   │   ├── UIPagination.jsx
│   │   │   │   │   ├── UIProgress.jsx
│   │   │   │   │   ├── UISkeleton.jsx
│   │   │   │   │   └── UISnackbar.jsx
│   │   │   │   └── basic
│   │   │   │       ├── UIList
│   │   │   │       │   ├── CustomList.jsx
│   │   │   │       │   ├── DisabledList.jsx
│   │   │   │       │   ├── FolderList.jsx
│   │   │   │       │   ├── NestedList.jsx
│   │   │   │       │   ├── RadioList.jsx
│   │   │   │       │   ├── SelectedListItem.jsx
│   │   │   │       │   ├── SimpleList.jsx
│   │   │   │       │   ├── VirtualizedList.jsx
│   │   │   │       │   └── index_sonic_dashboard.jsx
│   │   │   │       ├── UITabs
│   │   │   │       │   ├── ColorTabs.jsx
│   │   │   │       │   ├── DisabledTabs.jsx
│   │   │   │       │   ├── IconTabs.jsx
│   │   │   │       │   ├── SimpleTabs.jsx
│   │   │   │       │   ├── VerticalTabs.jsx
│   │   │   │       │   └── index_sonic_dashboard.jsx
│   │   │   │       ├── UIAccordion.jsx
│   │   │   │       ├── UIAvatar.jsx
│   │   │   │       ├── UIBadges.jsx
│   │   │   │       ├── UIBreadcrumb.jsx
│   │   │   │       ├── UICards.jsx
│   │   │   │       └── UIChip.jsx
│   │   │   ├── utilities
│   │   │   │   ├── Grid
│   │   │   │   │   ├── AutoGrid.jsx
│   │   │   │   │   ├── BasicGrid.jsx
│   │   │   │   │   ├── ColumnsGrid.jsx
│   │   │   │   │   ├── ComplexGrid.jsx
│   │   │   │   │   ├── GridItem.jsx
│   │   │   │   │   ├── MultipleBreakPoints.jsx
│   │   │   │   │   ├── NestedGrid.jsx
│   │   │   │   │   ├── SpacingGrid.jsx
│   │   │   │   │   └── index_sonic_dashboard.jsx
│   │   │   │   ├── Animation.jsx
│   │   │   │   ├── Color.jsx
│   │   │   │   ├── Shadow.jsx
│   │   │   │   └── Typography.jsx
│   │   │   └── widget
│   │   │       ├── Chart
│   │   │       │   ├── chart-data
│   │   │       │   │   ├── conversions-chart.jsx
│   │   │       │   │   ├── index_sonic_dashboard.jsx
│   │   │       │   │   ├── market-sale-chart.jsx
│   │   │       │   │   ├── percentage-chart.jsx
│   │   │       │   │   ├── revenue-chart.jsx
│   │   │       │   │   ├── sale-chart-1.jsx
│   │   │       │   │   ├── satisfaction-chart.jsx
│   │   │       │   │   ├── seo-chart-1.jsx
│   │   │       │   │   ├── seo-chart-2.jsx
│   │   │       │   │   ├── seo-chart-3.jsx
│   │   │       │   │   ├── seo-chart-4.jsx
│   │   │       │   │   ├── seo-chart-5.jsx
│   │   │       │   │   ├── seo-chart-6.jsx
│   │   │       │   │   ├── seo-chart-7.jsx
│   │   │       │   │   ├── seo-chart-8.jsx
│   │   │       │   │   ├── seo-chart-9.jsx
│   │   │       │   │   ├── total-value-graph-1.jsx
│   │   │       │   │   ├── total-value-graph-2.jsx
│   │   │       │   │   └── total-value-graph-3.jsx
│   │   │       │   ├── ConversionsChartCard.jsx
│   │   │       │   ├── MarketSaleChartCard.jsx
│   │   │       │   ├── RevenueChartCard.jsx
│   │   │       │   ├── SatisfactionChartCard.jsx
│   │   │       │   └── index_sonic_dashboard.jsx
│   │   │       ├── Data
│   │   │       │   ├── ActiveTickets.jsx
│   │   │       │   ├── ApplicationSales.jsx
│   │   │       │   ├── FeedsCard.jsx
│   │   │       │   ├── IncomingRequests.jsx
│   │   │       │   ├── LatestCustomers.jsx
│   │   │       │   ├── LatestMessages.jsx
│   │   │       │   ├── LatestOrder.jsx
│   │   │       │   ├── LatestPosts.jsx
│   │   │       │   ├── NewCustomers.jsx
│   │   │       │   ├── ProductSales.jsx
│   │   │       │   ├── ProjectTable.jsx
│   │   │       │   ├── RecentTickets.jsx
│   │   │       │   ├── TasksCard.jsx
│   │   │       │   ├── TeamMembers.jsx
│   │   │       │   ├── ToDoList.jsx
│   │   │       │   ├── TotalRevenue.jsx
│   │   │       │   ├── TrafficSources.jsx
│   │   │       │   ├── UserActivity.jsx
│   │   │       │   └── index_sonic_dashboard.jsx
│   │   │       └── Statistics
│   │   │           ├── CustomerSatisfactionCard.jsx
│   │   │           ├── IconGridCard.jsx
│   │   │           ├── ProjectTaskCard.jsx
│   │   │           ├── WeatherCard.jsx
│   │   │           └── index_sonic_dashboard.jsx
│   │   ├── SonicReactApp.jsx
│   │   ├── config.js
│   │   ├── index_sonic_dashboard.jsx
│   │   ├── reportWebVitals.js
│   │   ├── serviceWorker.jsx
│   │   └── vite-env.d.js
│   ├── .env
│   ├── .env.qa
│   ├── .gitignore
│   ├── .prettierrc
│   ├── .yarnrc.yml
│   ├── eslint.config.mjs
│   ├── favicon.svg
│   ├── index.html
│   ├── jsconfig.json
│   ├── jsconfig.node.json
│   ├── package-lock.json
│   ├── package.json
│   ├── vite.config.mjs
│   └── yarn.lock
├── .gitignore
├── README.md
├── launch_pad.py
└── requirements.txt
```

## File Descriptions

### Backend
- **backend/** – Python package containing the FastAPI server and alert processing logic.
- **config/** – JSON configuration files and the `config_loader.py` helper to read them.
- **console/** – Simple command line interface for Cyclone operations.
- **controllers/** – Entry points that orchestrate cyclone and monitor actions.
- **core/** – All domain modules for alerts, cyclone engine, hedging, monitoring, wallets and more.
- **data/** – DataLocker persistence layer and database helpers.
- **logs/** – Runtime log files such as `cyclone_log.txt`.
- **models/** – Pydantic/ORM models for alerts, portfolios, positions and wallets.
- **routes/** – FastAPI routers exposing REST endpoints.
- **services/** – Database and external service wrappers.
- **utils/** – Helper utilities including logging, schema validation and startup checks.
- **sonic_backend_app.py** – FastAPI application entrypoint used by Uvicorn.

### Frontend
- **frontend/** – React + Vite client application.
- **root files** – Configuration for ESLint, Vite and package dependencies.
- **src/App.jsx** – Mounts routes and context providers.
- **src/api/** – Wrapper functions for backend endpoints such as positions and wallets.
- **src/assets/** – Images and SCSS theme files.
- **src/config.js** – Frontend configuration constants.
- **src/contexts/** – Authentication and settings providers.
- **src/data/** – Sample location data used by the UI.
- **src/hooks/** – Reusable React hooks.
- **src/layout/** – Layout components like header, sidebar and minimal layout.
- **src/menu-items/** – Definitions for the sidebar navigation structure.
- **src/routes/** – React Router route groupings.
- **src/store/** – Redux store setup and slices.
- **src/themes/** – Material‑UI theme customization.
- **src/ui-component/** – Shared UI components and widgets.
- **src/views/** – Page level components including forms, charts and authentication views.
- **index.html / vite.config.mjs** – Vite app entry HTML and build configuration.

## Recent updates

- Wallet icons now appear in the portfolio table and asset icons show next to the
  asset type in the positions table. The images live under
  `frontend/static/images` and are loaded automatically based on the wallet or
  token name.
- The **Alert Thresholds** page includes an **Add Threshold** dialog used to add a
  new threshold. The dialog collects the alert type, metric key and low/medium/high
  values before persisting the record through the backend API.
- Running `scripts/initialize_database.py --seed-thresholds` populates default
  ranges for **Liquidation Distance** and **Profit** using `AlertThresholdSeeder`.

