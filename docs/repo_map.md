sonic1/
├── backend
│   ├── app.py
│   ├── routes
│   │   └── api.py
│   ├── controllers
│   │   ├── __init__.py
│   │   ├── cyclone_controller.py
│   │   ├── monitor_controller.py
│   │   └── logic.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   ├── position.py
│   │   ├── hedge.py
│   │   └── wallet.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── core_imports.py
│   │   ├── logging.py
│   │   ├── alert_core
│   │   │   ├── __init__.py
│   │   │   └── alert_services.py
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
│   │   └── wallet_core
│   │       ├── __init__.py
│   │       └── wallet_services.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── database_service.py
│   │   ├── xcom_service.py
│   │   └── external_api_service.py
│   ├── launch_pad.py
│   ├── cli
│   │   └── __init__.py

│   ├── cli
│   │   ├── __init__.py
│   │   └── launch_pad.py
│   └── config
│       ├── __init__.py
│       ├── config_loader.py
│       ├── active_traders.json
│       ├── alert_thresholds.json
│       └── sonic_config.json
└── frontend
    ├── .env
    ├── .env.qa
    ├── .gitignore
    ├── .prettierrc
    ├── .yarnrc.yml
    ├── eslint.config.mjs
    ├── favicon.svg
    ├── index.html
    ├── jsconfig.json
    ├── jsconfig.node.json
    ├── package-lock.json
    ├── package.json
    ├── src
    │   ├── App.jsx
    │   ├── api
    │   │   ├── menu.js
    │   │   └── products.js
    │   ├── assets
    │   │   ├── images
    │   │   │   ├── auth
    │   │   │   │   ├── auth-blue-card.svg
    │   │   │   │   ├── auth-forgot-pass-multi-card.svg
    │   │   │   │   ├── auth-mail-blue-card.svg
    │   │   │   │   ├── auth-pattern-dark.svg
    │   │   │   │   ├── auth-pattern.svg
    │   │   │   │   ├── auth-purple-card.svg
    │   │   │   │   ├── auth-reset-error-card.svg
    │   │   │   │   ├── auth-reset-purple-card.svg
    │   │   │   │   ├── auth-signup-blue-card.svg
    │   │   │   │   ├── auth-signup-white-card.svg
    │   │   │   │   ├── img-a2-checkmail.svg
    │   │   │   │   ├── img-a2-codevarify.svg
    │   │   │   │   ├── img-a2-forgotpass.svg
    │   │   │   │   ├── img-a2-grid-dark.svg
    │   │   │   │   ├── img-a2-grid.svg
    │   │   │   │   ├── img-a2-login.svg
    │   │   │   │   ├── img-a2-resetpass.svg
    │   │   │   │   └── img-a2-signup.svg
    │   │   │   ├── blog
    │   │   │   │   ├── blog-1.png
    │   │   │   │   ├── blog-2.png
    │   │   │   │   ├── blog-3.png
    │   │   │   │   ├── blog-4.png
    │   │   │   │   ├── blog-5.png
    │   │   │   │   ├── blog-6.png
    │   │   │   │   ├── blog-7.png
    │   │   │   │   ├── blog-8.png
    │   │   │   │   ├── library-1.png
    │   │   │   │   ├── library-2.png
    │   │   │   │   ├── library-3.png
    │   │   │   │   └── post-banner.png
    │   │   │   ├── cards
    │   │   │   │   ├── card-1.jpg
    │   │   │   │   ├── card-2.jpg
    │   │   │   │   └── card-3.jpg
    │   │   │   ├── customization
    │   │   │   │   ├── big.svg
    │   │   │   │   ├── horizontal.svg
    │   │   │   │   ├── ltr.svg
    │   │   │   │   ├── max.svg
    │   │   │   │   ├── mini.svg
    │   │   │   │   ├── rtl.svg
    │   │   │   │   ├── small.svg
    │   │   │   │   └── vertical.svg
    │   │   │   ├── e-commerce
    │   │   │   │   ├── card.png
    │   │   │   │   ├── cod.png
    │   │   │   │   ├── completed.png
    │   │   │   │   ├── discount.png
    │   │   │   │   ├── empty-dark.svg
    │   │   │   │   ├── empty.svg
    │   │   │   │   ├── mastercard.png
    │   │   │   │   ├── paypal.png
    │   │   │   │   ├── prod-1.png
    │   │   │   │   ├── prod-2.png
    │   │   │   │   ├── prod-3.png
    │   │   │   │   ├── prod-4.png
    │   │   │   │   ├── prod-5.png
    │   │   │   │   ├── prod-6.png
    │   │   │   │   ├── prod-7.png
    │   │   │   │   ├── prod-8.png
    │   │   │   │   ├── prod-9.png
    │   │   │   │   └── visa.png
    │   │   │   ├── i18n
    │   │   │   │   ├── china.svg
    │   │   │   │   ├── france.svg
    │   │   │   │   ├── romania.svg
    │   │   │   │   └── united-states.svg
    │   │   │   ├── icons
    │   │   │   │   ├── auth0.svg
    │   │   │   │   ├── aws.svg
    │   │   │   │   ├── earning.svg
    │   │   │   │   ├── facebook.svg
    │   │   │   │   ├── firebase.svg
    │   │   │   │   ├── google.svg
    │   │   │   │   ├── jwt.svg
    │   │   │   │   ├── linkedin.svg
    │   │   │   │   ├── supabase.svg
    │   │   │   │   └── twitter.svg
    │   │   │   ├── landing
    │   │   │   │   ├── bg-header.jpg
    │   │   │   │   ├── bg-heand.png
    │   │   │   │   ├── bg-hero-block-dark.png
    │   │   │   │   ├── bg-hero-block-light.png
    │   │   │   │   ├── bg-rtl-info-block-dark.png
    │   │   │   │   ├── bg-rtl-info-block-light.png
    │   │   │   │   ├── bg-rtl-info-dark.svg
    │   │   │   │   ├── bg-rtl-info-light.svg
    │   │   │   │   ├── customization-left.png
    │   │   │   │   ├── customization-right.png
    │   │   │   │   ├── footer-awards.png
    │   │   │   │   ├── footer-dribble.png
    │   │   │   │   ├── footer-freepik.png
    │   │   │   │   ├── frameworks
    │   │   │   │   │   ├── angular.svg
    │   │   │   │   │   ├── bootstrap.svg
    │   │   │   │   │   ├── codeigniter.svg
    │   │   │   │   │   ├── django.svg
    │   │   │   │   │   ├── dot-net.svg
    │   │   │   │   │   ├── flask.svg
    │   │   │   │   │   ├── full-stack.svg
    │   │   │   │   │   ├── shopify.svg
    │   │   │   │   │   └── vue.svg
    │   │   │   │   ├── hero-dashboard.png
    │   │   │   │   ├── hero-widget-1.png
    │   │   │   │   ├── hero-widget-2.png
    │   │   │   │   ├── offer
    │   │   │   │   │   ├── offer-1.png
    │   │   │   │   │   ├── offer-2.png
    │   │   │   │   │   ├── offer-3.png
    │   │   │   │   │   ├── offer-4.png
    │   │   │   │   │   ├── offer-5.png
    │   │   │   │   │   └── offer-6.png
    │   │   │   │   ├── pre-apps
    │   │   │   │   │   ├── slider-dark-1.png
    │   │   │   │   │   ├── slider-dark-10.png
    │   │   │   │   │   ├── slider-dark-11.png
    │   │   │   │   │   ├── slider-dark-2.png
    │   │   │   │   │   ├── slider-dark-3.png
    │   │   │   │   │   ├── slider-dark-4.png
    │   │   │   │   │   ├── slider-dark-5.png
    │   │   │   │   │   ├── slider-dark-6.png
    │   │   │   │   │   ├── slider-dark-7.png
    │   │   │   │   │   ├── slider-dark-8.png
    │   │   │   │   │   ├── slider-dark-9.png
    │   │   │   │   │   ├── slider-light-1.png
    │   │   │   │   │   ├── slider-light-10.png
    │   │   │   │   │   ├── slider-light-11.png
    │   │   │   │   │   ├── slider-light-2.png
    │   │   │   │   │   ├── slider-light-3.png
    │   │   │   │   │   ├── slider-light-4.png
    │   │   │   │   │   ├── slider-light-5.png
    │   │   │   │   │   ├── slider-light-6.png
    │   │   │   │   │   ├── slider-light-7.png
    │   │   │   │   │   ├── slider-light-8.png
    │   │   │   │   │   └── slider-light-9.png
    │   │   │   │   ├── tech-dark.svg
    │   │   │   │   ├── tech-light.svg
    │   │   │   │   └── widget-mail.svg
    │   │   │   ├── logo-dark.svg
    │   │   │   ├── logo.svg
    │   │   │   ├── maintenance
    │   │   │   │   ├── 500-error.svg
    │   │   │   │   ├── empty-dark.svg
    │   │   │   │   ├── empty.svg
    │   │   │   │   ├── img-bg-grid-dark.svg
    │   │   │   │   ├── img-bg-grid.svg
    │   │   │   │   ├── img-bg-parts.svg
    │   │   │   │   ├── img-build.svg
    │   │   │   │   ├── img-ct-dark-logo.png
    │   │   │   │   ├── img-ct-light-logo.png
    │   │   │   │   ├── img-error-bg-dark.svg
    │   │   │   │   ├── img-error-bg.svg
    │   │   │   │   ├── img-error-blue.svg
    │   │   │   │   ├── img-error-purple.svg
    │   │   │   │   ├── img-error-text.svg
    │   │   │   │   ├── img-soon-2.svg
    │   │   │   │   ├── img-soon-3.svg
    │   │   │   │   ├── img-soon-4.svg
    │   │   │   │   ├── img-soon-5.svg
    │   │   │   │   ├── img-soon-6.svg
    │   │   │   │   ├── img-soon-7.svg
    │   │   │   │   ├── img-soon-8.svg
    │   │   │   │   ├── img-soon-bg-grid-dark.svg
    │   │   │   │   ├── img-soon-bg-grid.svg
    │   │   │   │   ├── img-soon-bg.svg
    │   │   │   │   ├── img-soon-block.svg
    │   │   │   │   ├── img-soon-blue-block.svg
    │   │   │   │   ├── img-soon-grid-dark.svg
    │   │   │   │   ├── img-soon-grid.svg
    │   │   │   │   └── img-soon-purple-block.svg
    │   │   │   ├── pages
    │   │   │   │   ├── card-discover.png
    │   │   │   │   ├── card-master.png
    │   │   │   │   ├── card-visa.png
    │   │   │   │   ├── img-catalog1.png
    │   │   │   │   ├── img-catalog2.png
    │   │   │   │   └── img-catalog3.png
    │   │   │   ├── profile
    │   │   │   │   ├── img-gal-1.png
    │   │   │   │   ├── img-gal-10.png
    │   │   │   │   ├── img-gal-11.png
    │   │   │   │   ├── img-gal-12.png
    │   │   │   │   ├── img-gal-2.png
    │   │   │   │   ├── img-gal-3.png
    │   │   │   │   ├── img-gal-4.png
    │   │   │   │   ├── img-gal-5.png
    │   │   │   │   ├── img-gal-6.png
    │   │   │   │   ├── img-gal-7.png
    │   │   │   │   ├── img-gal-8.png
    │   │   │   │   ├── img-gal-9.png
    │   │   │   │   ├── img-profile-bg.png
    │   │   │   │   ├── img-profile1.png
    │   │   │   │   ├── img-profile2.jpg
    │   │   │   │   ├── img-profile3.jpg
    │   │   │   │   ├── profile-back-1.png
    │   │   │   │   ├── profile-back-10.png
    │   │   │   │   ├── profile-back-11.png
    │   │   │   │   ├── profile-back-12.png
    │   │   │   │   ├── profile-back-2.png
    │   │   │   │   ├── profile-back-3.png
    │   │   │   │   ├── profile-back-4.png
    │   │   │   │   ├── profile-back-5.png
    │   │   │   │   ├── profile-back-6.png
    │   │   │   │   ├── profile-back-7.png
    │   │   │   │   ├── profile-back-8.png
    │   │   │   │   └── profile-back-9.png
    │   │   │   ├── testaments
    │   │   │   │   ├── testaments-1.png
    │   │   │   │   ├── testaments-2.png
    │   │   │   │   ├── testaments-3.png
    │   │   │   │   └── testaments-4.png
    │   │   │   ├── upload
    │   │   │   │   └── upload.svg
    │   │   │   ├── users
    │   │   │   │   ├── avatar-1.png
    │   │   │   │   ├── avatar-10.png
    │   │   │   │   ├── avatar-11.png
    │   │   │   │   ├── avatar-12.png
    │   │   │   │   ├── avatar-2.png
    │   │   │   │   ├── avatar-3.png
    │   │   │   │   ├── avatar-4.png
    │   │   │   │   ├── avatar-5.png
    │   │   │   │   ├── avatar-6.png
    │   │   │   │   ├── avatar-7.png
    │   │   │   │   ├── avatar-8.png
    │   │   │   │   ├── avatar-9.png
    │   │   │   │   ├── img-user.png
    │   │   │   │   ├── profile.png
    │   │   │   │   └── user-round.svg
    │   │   │   └── widget
    │   │   │       ├── australia.jpg
    │   │   │       ├── brazil.jpg
    │   │   │       ├── dashboard-1.jpg
    │   │   │       ├── dashboard-2.jpg
    │   │   │       ├── germany.jpg
    │   │   │       ├── phone-1.jpg
    │   │   │       ├── phone-2.jpg
    │   │   │       ├── phone-3.jpg
    │   │   │       ├── phone-4.jpg
    │   │   │       ├── prod1.jpg
    │   │   │       ├── prod2.jpg
    │   │   │       ├── prod3.jpg
    │   │   │       ├── prod4.jpg
    │   │   │       ├── uk.jpg
    │   │   │       └── usa.jpg
    │   │   └── scss
    │   │       ├── _theme1.module.scss
    │   │       ├── _theme2.module.scss
    │   │       ├── _theme3.module.scss
    │   │       ├── _theme4.module.scss
    │   │       ├── _theme5.module.scss
    │   │       ├── _theme6.module.scss
    │   │       ├── _themes-vars.module.scss
    │   │       ├── scrollbar.scss
    │   │       ├── style.scss
    │   │       └── yet-another-react-lightbox.scss
    │   ├── config.js
    │   ├── contexts
    │   │   ├── AWSCognitoContext.jsx
    │   │   ├── Auth0Context.jsx
    │   │   ├── ConfigContext.jsx
    │   │   ├── FirebaseContext.jsx
    │   │   ├── JWTContext.jsx
    │   │   └── SupabaseContext.jsx
    │   ├── data
    │   │   └── location.js
    │   ├── hooks
    │   │   ├── useAuth.js
    │   │   ├── useConfig.js
    │   │   ├── useDataGrid.js
    │   │   ├── useLocalStorage.js
    │   │   ├── useMenuCollapse.js
    │   │   └── useScriptRef.js
    │   ├── header.jsx
    │   ├── layout
    │   │   ├── Customization
    │   │   │   ├── BorderRadius.jsx
    │   │   │   ├── BoxContainer.jsx
    │   │   │   ├── FontFamily.jsx
    │   │   │   ├── InputFilled.jsx
    │   │   │   ├── Layout.jsx
    │   │   │   ├── MenuOrientation.jsx
    │   │   │   ├── PresetColor.jsx
    │   │   │   ├── SidebarDrawer.jsx
    │   │   │   ├── ThemeMode.jsx
    │   │   │   └── header.jsx
    │   │   ├── MainLayout
    │   │   │   ├── Footer.jsx
    │   │   │   ├── Header
    │   │   │   │   ├── FullScreenSection
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── LocalizationSection
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── MegaMenuSection
    │   │   │   │   │   ├── Banner.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── MobileSection
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── NotificationSection
    │   │   │   │   │   ├── NotificationList.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ProfileSection
    │   │   │   │   │   ├── UpgradePlanCard.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── SearchSection
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── HorizontalBar.jsx
    │   │   │   ├── LogoSection
    │   │   │   │   └── header.jsx
    │   │   │   ├── MainContentStyled.js
    │   │   │   ├── MenuList
    │   │   │   │   ├── NavCollapse
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── NavGroup
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── NavItem
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── Sidebar
    │   │   │   │   ├── MenuCard
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── MiniDrawerStyled.jsx
    │   │   │   │   └── header.jsx
    │   │   │   └── header.jsx
    │   │   ├── MinimalLayout
    │   │   │   └── header.jsx
    │   │   ├── NavMotion.jsx
    │   │   ├── NavigationScroll.jsx
    │   │   └── SimpleLayout
    │   │       └── header.jsx
    │   ├── menu-items
    │   │   ├── application.js
    │   │   ├── dashboard.js
    │   │   ├── elements.js
    │   │   ├── forms.js
    │   │   ├── index.js
    │   │   ├── other.js
    │   │   ├── pages.js
    │   │   ├── sample-page.js
    │   │   ├── support.jsx
    │   │   ├── utilities.js
    │   │   └── widget.js
    │   ├── metrics
    │   │   ├── GTag.jsx
    │   │   ├── MicrosoftClarity.jsx
    │   │   ├── Notify.jsx
    │   │   └── header.jsx
    │   ├── reportWebVitals.js
    │   ├── routes
    │   │   ├── AuthenticationRoutes.jsx
    │   │   ├── ErrorBoundary.jsx
    │   │   ├── LoginRoutes.jsx
    │   │   ├── MainRoutes.jsx
    │   │   ├── SimpleRoutes.jsx
    │   │   └── header.jsx
    │   ├── serviceWorker.jsx
    │   ├── store
    │   │   ├── accountReducer.js
    │   │   ├── actions.js
    │   │   ├── constant.js
    │   │   ├── index.js
    │   │   ├── reducer.js
    │   │   └── slices
    │   │       ├── calendar.js
    │   │       ├── cart.js
    │   │       ├── chat.js
    │   │       ├── contact.js
    │   │       ├── customer.js
    │   │       ├── kanban.js
    │   │       ├── mail.js
    │   │       ├── product.js
    │   │       ├── snackbar.js
    │   │       └── user.js
    │   ├── themes
    │   │   ├── compStyleOverride.jsx
    │   │   ├── header.jsx
    │   │   ├── overrides
    │   │   │   ├── Chip.jsx
    │   │   │   └── index.js
    │   │   ├── palette.jsx
    │   │   ├── shadows.jsx
    │   │   └── typography.jsx
    │   ├── ui-component
    │   │   ├── Loadable.jsx
    │   │   ├── Loader.jsx
    │   │   ├── Locales.jsx
    │   │   ├── Logo.jsx
    │   │   ├── RTLLayout.jsx
    │   │   ├── cards
    │   │   │   ├── AnalyticsChartCard.jsx
    │   │   │   ├── AttachmentCard.jsx
    │   │   │   ├── AuthFooter.jsx
    │   │   │   ├── AuthSlider.jsx
    │   │   │   ├── BackgroundPattern1.jsx
    │   │   │   ├── BackgroundPattern2.jsx
    │   │   │   ├── BillCard.jsx
    │   │   │   ├── Blog
    │   │   │   │   ├── Categories.jsx
    │   │   │   │   ├── CommentCard.jsx
    │   │   │   │   ├── CreateBlogCard.jsx
    │   │   │   │   ├── DiscountCard.jsx
    │   │   │   │   ├── Drafts.jsx
    │   │   │   │   ├── HashtagsCard.jsx
    │   │   │   │   ├── HeadingTab.jsx
    │   │   │   │   ├── LikeCard.jsx
    │   │   │   │   ├── SocialCard.jsx
    │   │   │   │   ├── TopLikes.jsx
    │   │   │   │   ├── TrendingArticles.jsx
    │   │   │   │   └── VideoCard.jsx
    │   │   │   ├── CardSecondaryAction.jsx
    │   │   │   ├── ContactCard.jsx
    │   │   │   ├── ContactList.jsx
    │   │   │   ├── FloatingCart.jsx
    │   │   │   ├── FollowerCard.jsx
    │   │   │   ├── FriendRequestCard.jsx
    │   │   │   ├── FriendsCard.jsx
    │   │   │   ├── GalleryCard.jsx
    │   │   │   ├── HoverDataCard.jsx
    │   │   │   ├── HoverSocialCard.jsx
    │   │   │   ├── IconNumberCard.jsx
    │   │   │   ├── MainCard.jsx
    │   │   │   ├── Post
    │   │   │   │   ├── Comment
    │   │   │   │   │   ├── Reply
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── ProductCard.jsx
    │   │   │   ├── ProductReview.jsx
    │   │   │   ├── ReportCard.jsx
    │   │   │   ├── RevenueCard.jsx
    │   │   │   ├── RoundIconCard.jsx
    │   │   │   ├── SalesLineChartCard.jsx
    │   │   │   ├── SeoChartCard.jsx
    │   │   │   ├── SideIconCard.jsx
    │   │   │   ├── Skeleton
    │   │   │   │   ├── EarningCard.jsx
    │   │   │   │   ├── ImagePlaceholder.jsx
    │   │   │   │   ├── PopularCard.jsx
    │   │   │   │   ├── ProductPlaceholder.jsx
    │   │   │   │   ├── TotalGrowthBarChart.jsx
    │   │   │   │   └── TotalIncomeCard.jsx
    │   │   │   ├── SubCard.jsx
    │   │   │   ├── TotalIncomeDarkCard.jsx
    │   │   │   ├── TotalIncomeLightCard.jsx
    │   │   │   ├── TotalLineChartCard.jsx
    │   │   │   ├── UserCountCard.jsx
    │   │   │   ├── UserDetailsCard.jsx
    │   │   │   ├── UserProfileCard.jsx
    │   │   │   └── UserSimpleCard.jsx
    │   │   ├── extended
    │   │   │   ├── Accordion.jsx
    │   │   │   ├── AnimateButton.jsx
    │   │   │   ├── AppBar.jsx
    │   │   │   ├── Avatar.jsx
    │   │   │   ├── Breadcrumbs.jsx
    │   │   │   ├── Form
    │   │   │   │   ├── FormControl.jsx
    │   │   │   │   ├── FormControlSelect.jsx
    │   │   │   │   └── InputLabel.jsx
    │   │   │   ├── ImageList.jsx
    │   │   │   ├── Snackbar.jsx
    │   │   │   ├── Transitions.jsx
    │   │   │   └── notistack
    │   │   │       ├── ColorVariants.jsx
    │   │   │       ├── CustomComponent.jsx
    │   │   │       ├── Dense.jsx
    │   │   │       ├── DismissSnackBar.jsx
    │   │   │       ├── HideDuration.jsx
    │   │   │       ├── IconVariants.jsx
    │   │   │       ├── MaxSnackbar.jsx
    │   │   │       ├── PositioningSnackbar.jsx
    │   │   │       ├── PreventDuplicate.jsx
    │   │   │       ├── SnackBarAction.jsx
    │   │   │       ├── TransitionBar.jsx
    │   │   │       └── header.jsx
    │   │   └── third-party
    │   │       ├── Notistack.jsx
    │   │       ├── ReactQuill.jsx
    │   │       ├── dropzone
    │   │       │   ├── Avatar.jsx
    │   │       │   ├── FilePreview.jsx
    │   │       │   ├── MultiFile.jsx
    │   │       │   ├── PlaceHolderContent.jsx
    │   │       │   ├── RejectionFile.jsx
    │   │       │   └── SingleFile.jsx
    │   │       └── map
    │   │           ├── ControlPanelStyled.jsx
    │   │           ├── MapContainerStyled.jsx
    │   │           ├── MapControl.jsx
    │   │           ├── MapControlsStyled.jsx
    │   │           ├── MapMarker.jsx
    │   │           ├── MapPopup.jsx
    │   │           └── PopupStyled.jsx
    │   ├── utils
    │   │   ├── axios.js
    │   │   ├── getDropzoneData.js
    │   │   ├── getImageUrl.js
    │   │   ├── locales
    │   │   │   ├── en.json
    │   │   │   ├── fr.json
    │   │   │   ├── ro.json
    │   │   │   └── zh.json
    │   │   ├── password-strength.js
    │   │   └── route-guard
    │   │       ├── AuthGuard.jsx
    │   │       └── GuestGuard.jsx
    │   ├── views
    │   │   ├── application
    │   │   │   ├── blog
    │   │   │   │   ├── AddNewBlog
    │   │   │   │   │   ├── AddNewForm.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Dashboard
    │   │   │   │   │   ├── AnalyticsBarChart.jsx
    │   │   │   │   │   ├── RecentBlogList.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Details
    │   │   │   │   │   ├── BlogCommonCard.jsx
    │   │   │   │   │   ├── BlogDetailsCard.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── EditBlog
    │   │   │   │   │   ├── EditForm.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── GeneralSettings
    │   │   │   │   │   ├── Articles.jsx
    │   │   │   │   │   ├── Drafts.jsx
    │   │   │   │   │   ├── GeneralSetting.jsx
    │   │   │   │   │   ├── YourLibrary.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── List
    │   │   │   │   │   ├── BlogCommonCard.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── chart-data
    │   │   │   │   │   └── analytics-bar-charts.jsx
    │   │   │   │   └── data
    │   │   │   │       └── index.js
    │   │   │   ├── calendar
    │   │   │   │   ├── AddEventForm.jsx
    │   │   │   │   ├── CalendarStyled.jsx
    │   │   │   │   ├── ColorPalette.jsx
    │   │   │   │   ├── Toolbar.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── chat
    │   │   │   │   ├── AvatarStatus.jsx
    │   │   │   │   ├── ChartHistory.jsx
    │   │   │   │   ├── ChatDrawer.jsx
    │   │   │   │   ├── UserAvatar.jsx
    │   │   │   │   ├── UserDetails.jsx
    │   │   │   │   ├── UserList.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── contact
    │   │   │   │   ├── Card
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── List
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── UserDetails.jsx
    │   │   │   │   └── UserEdit.jsx
    │   │   │   ├── crm
    │   │   │   │   ├── ContactManagement
    │   │   │   │   │   ├── CommunicationHistory
    │   │   │   │   │   │   ├── Filter.jsx
    │   │   │   │   │   │   ├── HistoryTableBody.jsx
    │   │   │   │   │   │   ├── HistoryTableHeader.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   ├── ContactCard
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   ├── ContactList
    │   │   │   │   │   │   ├── AddContactDialog.jsx
    │   │   │   │   │   │   ├── AddContactDialogContent.jsx
    │   │   │   │   │   │   ├── ContactTableBody.jsx
    │   │   │   │   │   │   ├── ContactTableHeader.jsx
    │   │   │   │   │   │   ├── Filter.jsx
    │   │   │   │   │   │   ├── NewMessage.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── RemindersFollowUp
    │   │   │   │   │       ├── Filter.jsx
    │   │   │   │   │       ├── FollowupTableBody.jsx
    │   │   │   │   │       ├── FollowupTableHeader.jsx
    │   │   │   │   │       └── header.jsx
    │   │   │   │   ├── LeadManagement
    │   │   │   │   │   ├── LeadList
    │   │   │   │   │   │   ├── AddLeadDialog.jsx
    │   │   │   │   │   │   ├── AddLeadDialogBody.jsx
    │   │   │   │   │   │   ├── Filter.jsx
    │   │   │   │   │   │   ├── FilterLeadList.jsx
    │   │   │   │   │   │   ├── LeadDrawer.jsx
    │   │   │   │   │   │   ├── LeadTable.jsx
    │   │   │   │   │   │   ├── LeadTableBody.jsx
    │   │   │   │   │   │   ├── LeadTableHeader.jsx
    │   │   │   │   │   │   ├── NewMessage.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── Overview
    │   │   │   │   │       ├── LeadCards.jsx
    │   │   │   │   │       ├── LeadSource.jsx
    │   │   │   │   │       ├── LeadSummary.jsx
    │   │   │   │   │       ├── SalesPerformance.jsx
    │   │   │   │   │       ├── UpcomingTask.jsx
    │   │   │   │   │       └── header.jsx
    │   │   │   │   └── SalesManagement
    │   │   │   │       ├── Earning
    │   │   │   │       │   ├── EarningHeader.jsx
    │   │   │   │       │   ├── EarningTable.jsx
    │   │   │   │       │   ├── Filter.jsx
    │   │   │   │       │   ├── Overview.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       ├── Refund
    │   │   │   │       │   ├── Filter.jsx
    │   │   │   │       │   ├── Overview.jsx
    │   │   │   │       │   ├── RefundHeader.jsx
    │   │   │   │       │   ├── RefundTable.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       └── Statement
    │   │   │   │           ├── Filter.jsx
    │   │   │   │           ├── OverView.jsx
    │   │   │   │           ├── StatementHeader.jsx
    │   │   │   │           ├── StatementTable.jsx
    │   │   │   │           └── header.jsx
    │   │   │   ├── customer
    │   │   │   │   ├── CreateInvoice
    │   │   │   │   │   ├── AddItemPage.jsx
    │   │   │   │   │   ├── ProductsPage.jsx
    │   │   │   │   │   ├── TotalCard.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── CustomerList.jsx
    │   │   │   │   ├── OrderDetails
    │   │   │   │   │   ├── Details.jsx
    │   │   │   │   │   ├── Invoice.jsx
    │   │   │   │   │   ├── Status.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── OrderList.jsx
    │   │   │   │   ├── Product
    │   │   │   │   │   ├── ProductAdd.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── ProductReview
    │   │   │   │       ├── ReviewEdit.jsx
    │   │   │   │       └── header.jsx
    │   │   │   ├── e-commerce
    │   │   │   │   ├── Checkout
    │   │   │   │   │   ├── AddAddress.jsx
    │   │   │   │   │   ├── AddPaymentCard.jsx
    │   │   │   │   │   ├── AddressCard.jsx
    │   │   │   │   │   ├── BillingAddress.jsx
    │   │   │   │   │   ├── Cart.jsx
    │   │   │   │   │   ├── CartDiscount.jsx
    │   │   │   │   │   ├── CartEmpty.jsx
    │   │   │   │   │   ├── CouponCode.jsx
    │   │   │   │   │   ├── OrderComplete.jsx
    │   │   │   │   │   ├── OrderSummary.jsx
    │   │   │   │   │   ├── Payment.jsx
    │   │   │   │   │   ├── PaymentCard.jsx
    │   │   │   │   │   ├── PaymentOptions.js
    │   │   │   │   │   ├── PaymentSelect.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ColorOptions.js
    │   │   │   │   ├── ProductDetails
    │   │   │   │   │   ├── ProductDescription.jsx
    │   │   │   │   │   ├── ProductImages.jsx
    │   │   │   │   │   ├── ProductInfo.jsx
    │   │   │   │   │   ├── ProductReview.jsx
    │   │   │   │   │   ├── RelatedProducts.jsx
    │   │   │   │   │   ├── Specification.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ProductList.jsx
    │   │   │   │   └── Products
    │   │   │   │       ├── Colors.jsx
    │   │   │   │       ├── ProductEmpty.jsx
    │   │   │   │       ├── ProductFilter.jsx
    │   │   │   │       ├── ProductFilterView.jsx
    │   │   │   │       ├── SortOptions.js
    │   │   │   │       └── header.jsx
    │   │   │   ├── invoice
    │   │   │   │   ├── Client
    │   │   │   │   │   ├── AddClient
    │   │   │   │   │   │   ├── Address.jsx
    │   │   │   │   │   │   ├── ContactDetail.jsx
    │   │   │   │   │   │   ├── OtherDetail.jsx
    │   │   │   │   │   │   ├── PersonalInformation.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── ClientList
    │   │   │   │   │       ├── ClientDetails.jsx
    │   │   │   │   │       ├── ClientDrawer.jsx
    │   │   │   │   │       ├── ClientFilter.jsx
    │   │   │   │   │       ├── ClientTable.jsx
    │   │   │   │   │       ├── ClientTableHeader.jsx
    │   │   │   │   │       └── header.jsx
    │   │   │   │   ├── Create
    │   │   │   │   │   ├── AmountCard.jsx
    │   │   │   │   │   ├── ClientInfo.jsx
    │   │   │   │   │   ├── ItemList.jsx
    │   │   │   │   │   ├── SelectItem.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Dashboard
    │   │   │   │   │   ├── ClientInsights.jsx
    │   │   │   │   │   ├── QuickAdd.jsx
    │   │   │   │   │   ├── RecentActivity.jsx
    │   │   │   │   │   ├── RevenueBarChart.jsx
    │   │   │   │   │   ├── SupportHelp.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Details
    │   │   │   │   │   ├── DetailsTab.jsx
    │   │   │   │   │   ├── InvoiceTab.jsx
    │   │   │   │   │   ├── StatusTab.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Edit
    │   │   │   │   │   ├── AmountCard.jsx
    │   │   │   │   │   ├── ClientInfo.jsx
    │   │   │   │   │   ├── ItemList.jsx
    │   │   │   │   │   ├── SelectItem.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Items
    │   │   │   │   │   ├── AddItem.jsx
    │   │   │   │   │   └── ItemList
    │   │   │   │   │       ├── ItemDetails.jsx
    │   │   │   │   │       ├── ItemDrawer.jsx
    │   │   │   │   │       ├── ItemFilter.jsx
    │   │   │   │   │       ├── ItemTable.jsx
    │   │   │   │   │       ├── ItemTableHeader.jsx
    │   │   │   │   │       └── header.jsx
    │   │   │   │   ├── List
    │   │   │   │   │   ├── InvoiceFilter.jsx
    │   │   │   │   │   ├── InvoiceTable.jsx
    │   │   │   │   │   ├── InvoiceTableHeader.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Payment
    │   │   │   │   │   ├── AddPayment
    │   │   │   │   │   │   ├── PaymentTable.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   ├── PaymentDetails
    │   │   │   │   │   │   ├── PaymentTable.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── PaymentList
    │   │   │   │   │       ├── Overview.jsx
    │   │   │   │   │       ├── PaymentFilter.jsx
    │   │   │   │   │       ├── PaymentTable.jsx
    │   │   │   │   │       ├── PaymentTableHeader.jsx
    │   │   │   │   │       └── header.jsx
    │   │   │   │   └── chart-data
    │   │   │   │       ├── header.jsx
    │   │   │   │       ├── invoice-chart-1.jsx
    │   │   │   │       ├── invoice-chart-2.jsx
    │   │   │   │       ├── invoice-chart-3.jsx
    │   │   │   │       ├── invoice-chart-4.jsx
    │   │   │   │       └── revenue-bar-chart.jsx
    │   │   │   ├── kanban
    │   │   │   │   ├── Backlogs
    │   │   │   │   │   ├── AddItem.jsx
    │   │   │   │   │   ├── AddStory.jsx
    │   │   │   │   │   ├── AddStoryComment.jsx
    │   │   │   │   │   ├── AlertStoryDelete.jsx
    │   │   │   │   │   ├── EditStory.jsx
    │   │   │   │   │   ├── Items.jsx
    │   │   │   │   │   ├── StoryComment.jsx
    │   │   │   │   │   ├── UserStory.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Board
    │   │   │   │   │   ├── AddColumn.jsx
    │   │   │   │   │   ├── AddItem.jsx
    │   │   │   │   │   ├── AddItemComment.jsx
    │   │   │   │   │   ├── AlertColumnDelete.jsx
    │   │   │   │   │   ├── AlertItemDelete.jsx
    │   │   │   │   │   ├── Columns.jsx
    │   │   │   │   │   ├── EditColumn.jsx
    │   │   │   │   │   ├── EditItem.jsx
    │   │   │   │   │   ├── ItemComment.jsx
    │   │   │   │   │   ├── ItemDetails.jsx
    │   │   │   │   │   ├── Items.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── mail
    │   │   │   │   ├── ComposeDialog.jsx
    │   │   │   │   ├── MailDetails.jsx
    │   │   │   │   ├── MailDrawer.jsx
    │   │   │   │   ├── MailEmpty.jsx
    │   │   │   │   ├── MailList.jsx
    │   │   │   │   ├── MailListHeader.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── map
    │   │   │   │   ├── header.jsx
    │   │   │   │   └── maps
    │   │   │   │       ├── GeoJSONAnimation.jsx
    │   │   │   │       ├── HighlightByFilter.jsx
    │   │   │   │       ├── MarkersPopups.jsx
    │   │   │   │       ├── change-theme
    │   │   │   │       │   ├── control-panel.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       ├── clusters-map
    │   │   │   │       │   ├── header.jsx
    │   │   │   │       │   └── layers.js
    │   │   │   │       ├── draggable-marker
    │   │   │   │       │   ├── control-panel.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       ├── heatmap
    │   │   │   │       │   ├── control-panel.jsx
    │   │   │   │       │   ├── header.jsx
    │   │   │   │       │   └── map-style.js
    │   │   │   │       ├── interaction-map
    │   │   │   │       │   ├── control-panel.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       ├── side-by-side
    │   │   │   │       │   ├── control-panel.jsx
    │   │   │   │       │   └── header.jsx
    │   │   │   │       └── viewport-animation
    │   │   │   │           ├── control-panel.jsx
    │   │   │   │           └── header.jsx
    │   │   │   └── users
    │   │   │       ├── account-profile
    │   │   │       │   ├── Profile1
    │   │   │       │   │   ├── ChangePassword.jsx
    │   │   │       │   │   ├── MyAccount.jsx
    │   │   │       │   │   ├── PersonalAccount.jsx
    │   │   │       │   │   ├── Profile.jsx
    │   │   │       │   │   ├── Settings.jsx
    │   │   │       │   │   └── header.jsx
    │   │   │       │   ├── Profile2
    │   │   │       │   │   ├── Billing.jsx
    │   │   │       │   │   ├── ChangePassword.jsx
    │   │   │       │   │   ├── Payment.jsx
    │   │   │       │   │   ├── UserProfile.jsx
    │   │   │       │   │   └── header.jsx
    │   │   │       │   └── Profile3
    │   │   │       │       ├── Billing.jsx
    │   │   │       │       ├── Notifications.jsx
    │   │   │       │       ├── Profile.jsx
    │   │   │       │       ├── Security.jsx
    │   │   │       │       └── header.jsx
    │   │   │       ├── card
    │   │   │       │   ├── CardStyle1.jsx
    │   │   │       │   ├── CardStyle2.jsx
    │   │   │       │   └── CardStyle3.jsx
    │   │   │       ├── list
    │   │   │       │   ├── Style1
    │   │   │       │   │   ├── UserList.jsx
    │   │   │       │   │   └── header.jsx
    │   │   │       │   └── Style2
    │   │   │       │       ├── UserList.jsx
    │   │   │       │       └── header.jsx
    │   │   │       └── social-profile
    │   │   │           ├── Followers.jsx
    │   │   │           ├── FriendRequest.jsx
    │   │   │           ├── Friends.jsx
    │   │   │           ├── Gallery.jsx
    │   │   │           ├── Profile.jsx
    │   │   │           └── header.jsx
    │   │   ├── dashboard
    │   │   │   ├── Analytics
    │   │   │   │   ├── LatestCustomerTableCard.jsx
    │   │   │   │   ├── MarketShareAreaChartCard.jsx
    │   │   │   │   ├── TotalRevenueCard.jsx
    │   │   │   │   ├── chart-data
    │   │   │   │   │   └── market-share-area-chart.jsx
    │   │   │   │   └── header.jsx
    │   │   │   └── Default
    │   │   │       ├── BajajAreaChartCard.jsx
    │   │   │       ├── EarningCard.jsx
    │   │   │       ├── PopularCard.jsx
    │   │   │       ├── TotalGrowthBarChart.jsx
    │   │   │       ├── TotalOrderLineChartCard.jsx
    │   │   │       ├── chart-data
    │   │   │       │   ├── bajaj-area-chart.jsx
    │   │   │       │   ├── total-growth-bar-chart.jsx
    │   │   │       │   ├── total-order-month-line-chart.jsx
    │   │   │       │   └── total-order-year-line-chart.jsx
    │   │   │       └── header.jsx
    │   │   ├── forms
    │   │   │   ├── chart
    │   │   │   │   ├── Apexchart
    │   │   │   │   │   ├── ApexAreaChart.jsx
    │   │   │   │   │   ├── ApexBarChart.jsx
    │   │   │   │   │   ├── ApexColumnChart.jsx
    │   │   │   │   │   ├── ApexLineChart.jsx
    │   │   │   │   │   ├── ApexMixedChart.jsx
    │   │   │   │   │   ├── ApexPieChart.jsx
    │   │   │   │   │   ├── ApexPolarChart.jsx
    │   │   │   │   │   ├── ApexRedialChart.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── OrgChart
    │   │   │   │       ├── Card.jsx
    │   │   │   │       ├── DataCard.jsx
    │   │   │   │       ├── LinkedIn.jsx
    │   │   │   │       ├── MeetIcon.jsx
    │   │   │   │       ├── SkypeIcon.jsx
    │   │   │   │       └── header.jsx
    │   │   │   ├── components
    │   │   │   │   ├── AutoComplete.jsx
    │   │   │   │   ├── Button.jsx
    │   │   │   │   ├── Checkbox.jsx
    │   │   │   │   ├── DateTime
    │   │   │   │   │   ├── CustomDateTime.jsx
    │   │   │   │   │   ├── LandscapeDateTime.jsx
    │   │   │   │   │   ├── ViewRendererDateTime.jsx
    │   │   │   │   │   ├── ViewsDateTimePicker.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Radio.jsx
    │   │   │   │   ├── Slider
    │   │   │   │   │   ├── BasicSlider.jsx
    │   │   │   │   │   ├── DisableSlider.jsx
    │   │   │   │   │   ├── LabelSlider.jsx
    │   │   │   │   │   ├── PopupSlider.jsx
    │   │   │   │   │   ├── StepSlider.jsx
    │   │   │   │   │   ├── VerticalSlider.jsx
    │   │   │   │   │   ├── VolumeSlider.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Switch.jsx
    │   │   │   │   └── TextField.jsx
    │   │   │   ├── data-grid
    │   │   │   │   ├── ColumnGroups
    │   │   │   │   │   ├── BasicColumnGroup.jsx
    │   │   │   │   │   ├── CustomColumnGroup.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ColumnMenu
    │   │   │   │   │   ├── AddMenuItem.jsx
    │   │   │   │   │   ├── ColumnMenu.jsx
    │   │   │   │   │   ├── CustomMenu.jsx
    │   │   │   │   │   ├── DisableMenu.jsx
    │   │   │   │   │   ├── HideMenuItem.jsx
    │   │   │   │   │   ├── OverrideMenu.jsx
    │   │   │   │   │   ├── ReorderingMenu.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ColumnVirtualization
    │   │   │   │   │   ├── Virtualization.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ColumnVisibility
    │   │   │   │   │   ├── ControlledVisibility.jsx
    │   │   │   │   │   ├── InitializeColumnVisibility.jsx
    │   │   │   │   │   ├── VisibilityPanel.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── DataGridBasic
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── InLineEditing
    │   │   │   │   │   ├── AutoStop.jsx
    │   │   │   │   │   ├── ConfirmationSave.jsx
    │   │   │   │   │   ├── Controlled.jsx
    │   │   │   │   │   ├── CustomEdit.jsx
    │   │   │   │   │   ├── DisableEditing.jsx
    │   │   │   │   │   ├── EditableColumn.jsx
    │   │   │   │   │   ├── EditableRow.jsx
    │   │   │   │   │   ├── EditingEvents.jsx
    │   │   │   │   │   ├── FullFeatured.jsx
    │   │   │   │   │   ├── ParserSetter.jsx
    │   │   │   │   │   ├── ServerValidation.jsx
    │   │   │   │   │   ├── Validation.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── QuickFilter
    │   │   │   │   │   ├── CustomFilter.jsx
    │   │   │   │   │   ├── ExcludeHiddenColumns.jsx
    │   │   │   │   │   ├── Initialize.jsx
    │   │   │   │   │   ├── ParsingValues.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── SaveRestoreState
    │   │   │   │       ├── InitialState.jsx
    │   │   │   │       ├── UseGridSelector.jsx
    │   │   │   │       └── header.jsx
    │   │   │   ├── forms-validation
    │   │   │   │   ├── AutocompleteForms.jsx
    │   │   │   │   ├── CheckboxForms.jsx
    │   │   │   │   ├── InstantFeedback.jsx
    │   │   │   │   ├── LoginForms.jsx
    │   │   │   │   ├── RadioGroupForms.jsx
    │   │   │   │   ├── SelectForms.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── forms-wizard
    │   │   │   │   ├── BasicWizard
    │   │   │   │   │   ├── AddressForm.jsx
    │   │   │   │   │   ├── PaymentForm.jsx
    │   │   │   │   │   ├── Review.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── ValidationWizard
    │   │   │   │   │   ├── AddressForm.jsx
    │   │   │   │   │   ├── PaymentForm.jsx
    │   │   │   │   │   ├── Review.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── layouts
    │   │   │   │   ├── ActionBar.jsx
    │   │   │   │   ├── Layouts.jsx
    │   │   │   │   ├── MultiColumnForms.jsx
    │   │   │   │   └── StickyActionBar.jsx
    │   │   │   ├── plugins
    │   │   │   │   ├── AutoComplete.jsx
    │   │   │   │   ├── Clipboard.jsx
    │   │   │   │   ├── Dropzone.jsx
    │   │   │   │   ├── Editor.jsx
    │   │   │   │   ├── Mask.jsx
    │   │   │   │   ├── Modal
    │   │   │   │   │   ├── ServerModal.jsx
    │   │   │   │   │   ├── SimpleModal.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── Recaptcha.jsx
    │   │   │   │   └── Tooltip.jsx
    │   │   │   └── tables
    │   │   │       ├── TableBasic.jsx
    │   │   │       ├── TableCollapsible.jsx
    │   │   │       ├── TableData.jsx
    │   │   │       ├── TableDense.jsx
    │   │   │       ├── TableEnhanced.jsx
    │   │   │       ├── TableExports.jsx
    │   │   │       ├── TableStickyHead.jsx
    │   │   │       └── TablesCustomized.jsx
    │   │   ├── pages
    │   │   │   ├── authentication
    │   │   │   │   ├── AuthCardWrapper.jsx
    │   │   │   │   ├── AuthWrapper1.jsx
    │   │   │   │   ├── AuthWrapper2.jsx
    │   │   │   │   ├── CheckMail.jsx
    │   │   │   │   ├── CodeVerification.jsx
    │   │   │   │   ├── ForgotPassword.jsx
    │   │   │   │   ├── Login.jsx
    │   │   │   │   ├── LoginProvider.jsx
    │   │   │   │   ├── Register.jsx
    │   │   │   │   ├── ResetPassword.jsx
    │   │   │   │   ├── ViewOnlyAlert.jsx
    │   │   │   │   ├── auth0
    │   │   │   │   │   ├── AuthCodeVerification.jsx
    │   │   │   │   │   ├── AuthForgotPassword.jsx
    │   │   │   │   │   ├── AuthLogin.jsx
    │   │   │   │   │   ├── AuthRegister.jsx
    │   │   │   │   │   └── AuthResetPassword.jsx
    │   │   │   │   ├── authentication1
    │   │   │   │   │   ├── CheckMail1.jsx
    │   │   │   │   │   ├── CodeVerification1.jsx
    │   │   │   │   │   ├── ForgotPassword1.jsx
    │   │   │   │   │   ├── Login1.jsx
    │   │   │   │   │   ├── Register1.jsx
    │   │   │   │   │   └── ResetPassword1.jsx
    │   │   │   │   ├── authentication2
    │   │   │   │   │   ├── CheckMail2.jsx
    │   │   │   │   │   ├── CodeVerification2.jsx
    │   │   │   │   │   ├── ForgotPassword2.jsx
    │   │   │   │   │   ├── Login2.jsx
    │   │   │   │   │   ├── Register2.jsx
    │   │   │   │   │   └── ResetPassword2.jsx
    │   │   │   │   ├── aws
    │   │   │   │   │   ├── AuthCodeVerification.jsx
    │   │   │   │   │   ├── AuthForgotPassword.jsx
    │   │   │   │   │   ├── AuthLogin.jsx
    │   │   │   │   │   ├── AuthRegister.jsx
    │   │   │   │   │   └── AuthResetPassword.jsx
    │   │   │   │   ├── firebase
    │   │   │   │   │   ├── AuthCodeVerification.jsx
    │   │   │   │   │   ├── AuthForgotPassword.jsx
    │   │   │   │   │   ├── AuthLogin.jsx
    │   │   │   │   │   ├── AuthRegister.jsx
    │   │   │   │   │   ├── AuthResetPassword.jsx
    │   │   │   │   │   └── FirebaseSocial.jsx
    │   │   │   │   ├── jwt
    │   │   │   │   │   ├── AuthCodeVerification.jsx
    │   │   │   │   │   ├── AuthForgotPassword.jsx
    │   │   │   │   │   ├── AuthLogin.jsx
    │   │   │   │   │   ├── AuthRegister.jsx
    │   │   │   │   │   └── AuthResetPassword.jsx
    │   │   │   │   └── supabase
    │   │   │   │       ├── AuthCodeVerification.jsx
    │   │   │   │       ├── AuthForgotPassword.jsx
    │   │   │   │       ├── AuthLogin.jsx
    │   │   │   │       ├── AuthRegister.jsx
    │   │   │   │       └── AuthResetPassword.jsx
    │   │   │   ├── contact-us
    │   │   │   │   ├── ContactCard.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── landing
    │   │   │   │   ├── Animation.jsx
    │   │   │   │   ├── CardData.js
    │   │   │   │   ├── CardSection.jsx
    │   │   │   │   ├── CustomizeSection.jsx
    │   │   │   │   ├── FeatureSection.jsx
    │   │   │   │   ├── FooterSection.jsx
    │   │   │   │   ├── FrameworkSection.jsx
    │   │   │   │   ├── HeaderSection.jsx
    │   │   │   │   ├── IncludeSection.jsx
    │   │   │   │   ├── PeopleCard.jsx
    │   │   │   │   ├── PeopleSection.jsx
    │   │   │   │   ├── PreBuildDashBoard.jsx
    │   │   │   │   ├── RtlInfoSection.jsx
    │   │   │   │   ├── StartupProjectSection.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── maintenance
    │   │   │   │   ├── ComingSoon
    │   │   │   │   │   ├── ComingSoon1
    │   │   │   │   │   │   ├── MailerSubscriber.jsx
    │   │   │   │   │   │   ├── Slider.jsx
    │   │   │   │   │   │   └── header.jsx
    │   │   │   │   │   └── ComingSoon2.jsx
    │   │   │   │   ├── Error.jsx
    │   │   │   │   ├── Error500.jsx
    │   │   │   │   └── UnderConstruction.jsx
    │   │   │   ├── pricing
    │   │   │   │   ├── Price1.jsx
    │   │   │   │   └── Price2.jsx
    │   │   │   └── saas-pages
    │   │   │       ├── Faqs.jsx
    │   │   │       └── PrivacyPolicy.jsx
    │   │   ├── sample-page
    │   │   │   └── header.jsx
    │   │   ├── ui-elements
    │   │   │   ├── advance
    │   │   │   │   ├── UIAlert.jsx
    │   │   │   │   ├── UIDialog
    │   │   │   │   │   ├── AlertDialog.jsx
    │   │   │   │   │   ├── AlertDialogSlide.jsx
    │   │   │   │   │   ├── ConfirmationDialog.jsx
    │   │   │   │   │   ├── CustomizedDialogs.jsx
    │   │   │   │   │   ├── DraggableDialog.jsx
    │   │   │   │   │   ├── FormDialog.jsx
    │   │   │   │   │   ├── FullScreenDialog.jsx
    │   │   │   │   │   ├── MaxWidthDialog.jsx
    │   │   │   │   │   ├── ResponsiveDialog.jsx
    │   │   │   │   │   ├── ScrollDialog.jsx
    │   │   │   │   │   ├── SimpleDialog.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── UIPagination.jsx
    │   │   │   │   ├── UIProgress.jsx
    │   │   │   │   ├── UIRating
    │   │   │   │   │   ├── CustomizedRatings.jsx
    │   │   │   │   │   ├── HalfRating.jsx
    │   │   │   │   │   ├── HoverRating.jsx
    │   │   │   │   │   ├── SimpleRating.jsx
    │   │   │   │   │   ├── SizeRating.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── UISkeleton.jsx
    │   │   │   │   ├── UISnackbar.jsx
    │   │   │   │   ├── UISpeeddial
    │   │   │   │   │   ├── OpenIconSpeedDial.jsx
    │   │   │   │   │   ├── SimpleSpeedDials.jsx
    │   │   │   │   │   ├── SpeedDialTooltipOpen.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── UITimeline
    │   │   │   │   │   ├── AlternateTimeline.jsx
    │   │   │   │   │   ├── BasicTimeline.jsx
    │   │   │   │   │   ├── ColorsTimeline.jsx
    │   │   │   │   │   ├── CustomizedTimeline.jsx
    │   │   │   │   │   ├── OppositeContentTimeline.jsx
    │   │   │   │   │   ├── OutlinedTimeline.jsx
    │   │   │   │   │   ├── RightAlignedTimeline.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   ├── UIToggleButton
    │   │   │   │   │   ├── CustomizedDividers.jsx
    │   │   │   │   │   ├── ExclusiveToggleButtons.jsx
    │   │   │   │   │   ├── StandaloneToggleButton.jsx
    │   │   │   │   │   ├── ToggleButtonNotEmpty.jsx
    │   │   │   │   │   ├── ToggleButtonSizes.jsx
    │   │   │   │   │   ├── ToggleButtonsMultiple.jsx
    │   │   │   │   │   ├── VerticalToggleButtons.jsx
    │   │   │   │   │   └── header.jsx
    │   │   │   │   └── UITreeview
    │   │   │   │       ├── ControlledTreeView.jsx
    │   │   │   │       ├── CustomizedTreeView.jsx
    │   │   │   │       ├── FileSystemNavigator.jsx
    │   │   │   │       ├── GmailTreeView.jsx
    │   │   │   │       ├── MultiSelectTreeView.jsx
    │   │   │   │       ├── RecursiveTreeView.jsx
    │   │   │   │       └── header.jsx
    │   │   │   └── basic
    │   │   │       ├── UIAccordion.jsx
    │   │   │       ├── UIAvatar.jsx
    │   │   │       ├── UIBadges.jsx
    │   │   │       ├── UIBreadcrumb.jsx
    │   │   │       ├── UICards.jsx
    │   │   │       ├── UIChip.jsx
    │   │   │       ├── UIList
    │   │   │       │   ├── CustomList.jsx
    │   │   │       │   ├── DisabledList.jsx
    │   │   │       │   ├── FolderList.jsx
    │   │   │       │   ├── NestedList.jsx
    │   │   │       │   ├── RadioList.jsx
    │   │   │       │   ├── SelectedListItem.jsx
    │   │   │       │   ├── SimpleList.jsx
    │   │   │       │   ├── VirtualizedList.jsx
    │   │   │       │   └── header.jsx
    │   │   │       └── UITabs
    │   │   │           ├── ColorTabs.jsx
    │   │   │           ├── DisabledTabs.jsx
    │   │   │           ├── IconTabs.jsx
    │   │   │           ├── SimpleTabs.jsx
    │   │   │           ├── VerticalTabs.jsx
    │   │   │           └── header.jsx
    │   │   ├── utilities
    │   │   │   ├── Animation.jsx
    │   │   │   ├── Color.jsx
    │   │   │   ├── Grid
    │   │   │   │   ├── AutoGrid.jsx
    │   │   │   │   ├── BasicGrid.jsx
    │   │   │   │   ├── ColumnsGrid.jsx
    │   │   │   │   ├── ComplexGrid.jsx
    │   │   │   │   ├── GridItem.jsx
    │   │   │   │   ├── MultipleBreakPoints.jsx
    │   │   │   │   ├── NestedGrid.jsx
    │   │   │   │   ├── SpacingGrid.jsx
    │   │   │   │   └── header.jsx
    │   │   │   ├── Shadow.jsx
    │   │   │   └── Typography.jsx
    │   │   └── widget
    │   │       ├── Chart
    │   │       │   ├── ConversionsChartCard.jsx
    │   │       │   ├── MarketSaleChartCard.jsx
    │   │       │   ├── RevenueChartCard.jsx
    │   │       │   ├── SatisfactionChartCard.jsx
    │   │       │   ├── chart-data
    │   │       │   │   ├── conversions-chart.jsx
    │   │       │   │   ├── header.jsx
    │   │       │   │   ├── market-sale-chart.jsx
    │   │       │   │   ├── percentage-chart.jsx
    │   │       │   │   ├── revenue-chart.jsx
    │   │       │   │   ├── sale-chart-1.jsx
    │   │       │   │   ├── satisfaction-chart.jsx
    │   │       │   │   ├── seo-chart-1.jsx
    │   │       │   │   ├── seo-chart-2.jsx
    │   │       │   │   ├── seo-chart-3.jsx
    │   │       │   │   ├── seo-chart-4.jsx
    │   │       │   │   ├── seo-chart-5.jsx
    │   │       │   │   ├── seo-chart-6.jsx
    │   │       │   │   ├── seo-chart-7.jsx
    │   │       │   │   ├── seo-chart-8.jsx
    │   │       │   │   ├── seo-chart-9.jsx
    │   │       │   │   ├── total-value-graph-1.jsx
    │   │       │   │   ├── total-value-graph-2.jsx
    │   │       │   │   └── total-value-graph-3.jsx
    │   │       │   └── header.jsx
    │   │       ├── Data
    │   │       │   ├── ActiveTickets.jsx
    │   │       │   ├── ApplicationSales.jsx
    │   │       │   ├── FeedsCard.jsx
    │   │       │   ├── IncomingRequests.jsx
    │   │       │   ├── LatestCustomers.jsx
    │   │       │   ├── LatestMessages.jsx
    │   │       │   ├── LatestOrder.jsx
    │   │       │   ├── LatestPosts.jsx
    │   │       │   ├── NewCustomers.jsx
    │   │       │   ├── ProductSales.jsx
    │   │       │   ├── ProjectTable.jsx
    │   │       │   ├── RecentTickets.jsx
    │   │       │   ├── TasksCard.jsx
    │   │       │   ├── TeamMembers.jsx
    │   │       │   ├── ToDoList.jsx
    │   │       │   ├── TotalRevenue.jsx
    │   │       │   ├── TrafficSources.jsx
    │   │       │   ├── UserActivity.jsx
    │   │       │   └── header.jsx
    │   │       └── Statistics
    │   │           ├── CustomerSatisfactionCard.jsx
    │   │           ├── IconGridCard.jsx
    │   │           ├── ProjectTaskCard.jsx
    │   │           ├── WeatherCard.jsx
    │   │           └── header.jsx
    │   └── vite-env.d.js
    ├── vite.config.mjs
    └── yarn.lock
