# Frontend Repository Map

This file lists every folder and file under `frontend/`.

```txt
frontend
├── .env
├── .env.qa
├── .gitignore
├── .prettierrc
├── .yarn
│   └── install-state.gz
├── .yarnrc.yml
├── __tests__
│   ├── AlertThresholdInteractions.test.jsx
│   ├── AlertThresholdPage.test.jsx
│   ├── DonutCountdown.test.jsx
│   ├── MonitorManager.test.jsx
│   ├── PositionsTableCard.test.jsx
│   └── ThresholdTable.test.jsx
├── babel.config.js
├── eslint.config.mjs
├── favicon.svg
├── index.html
├── jest.config.js
├── jsconfig.json
├── jsconfig.node.json
├── package-lock.json
├── package.json
├── postcss.config.cjs
├── public
│   └── abstract_mural.png
├── src
│   ├── App.jsx
│   ├── api
│   │   ├── alertThresholds.js
│   │   ├── cyclone.js
│   │   ├── menu.js
│   │   ├── monitorStatus.js
│   │   ├── portfolio.js
│   │   ├── positions.js
│   │   ├── prices.js
│   │   ├── session.js
│   │   ├── sonicMonitor.js
│   │   ├── thresholdApi.js
│   │   ├── traders.js
│   │   ├── wallets.js
│   │   └── xcom.js
│   ├── assets
│   │   ├── images
│   │   │   ├── auth
│   │   │   │   ├── auth-blue-card.svg
│   │   │   │   ├── auth-forgot-pass-multi-card.svg
│   │   │   │   ├── auth-mail-blue-card.svg
│   │   │   │   ├── auth-pattern-dark.svg
│   │   │   │   ├── auth-pattern.svg
│   │   │   │   ├── auth-purple-card.svg
│   │   │   │   ├── auth-reset-error-card.svg
│   │   │   │   ├── auth-reset-purple-card.svg
│   │   │   │   ├── auth-signup-blue-card.svg
│   │   │   │   ├── auth-signup-white-card.svg
│   │   │   │   ├── img-a2-checkmail.svg
│   │   │   │   ├── img-a2-codevarify.svg
│   │   │   │   ├── img-a2-forgotpass.svg
│   │   │   │   ├── img-a2-grid-dark.svg
│   │   │   │   ├── img-a2-grid.svg
│   │   │   │   ├── img-a2-login.svg
│   │   │   │   ├── img-a2-resetpass.svg
│   │   │   │   └── img-a2-signup.svg
│   │   │   ├── blog
│   │   │   │   ├── blog-1.png
│   │   │   │   ├── blog-2.png
│   │   │   │   ├── blog-3.png
│   │   │   │   ├── blog-4.png
│   │   │   │   ├── blog-5.png
│   │   │   │   ├── blog-6.png
│   │   │   │   ├── blog-7.png
│   │   │   │   ├── blog-8.png
│   │   │   │   ├── library-1.png
│   │   │   │   ├── library-2.png
│   │   │   │   ├── library-3.png
│   │   │   │   └── post-banner.png
│   │   │   ├── customization
│   │   │   │   ├── big.svg
│   │   │   │   ├── horizontal.svg
│   │   │   │   ├── ltr.svg
│   │   │   │   ├── max.svg
│   │   │   │   ├── mini.svg
│   │   │   │   ├── rtl.svg
│   │   │   │   ├── small.svg
│   │   │   │   └── vertical.svg
│   │   │   ├── icons
│   │   │   │   ├── auth0.svg
│   │   │   │   ├── aws.svg
│   │   │   │   ├── earning.svg
│   │   │   │   ├── facebook.svg
│   │   │   │   ├── firebase.svg
│   │   │   │   ├── google.svg
│   │   │   │   ├── jwt.svg
│   │   │   │   ├── linkedin.svg
│   │   │   │   ├── supabase.svg
│   │   │   │   └── twitter.svg
│   │   │   ├── landing
│   │   │   │   └── pre-apps
│   │   │   │       ├── slider-dark-1.png
│   │   │   │       ├── slider-dark-2.png
│   │   │   │       ├── slider-dark-3.png
│   │   │   │       ├── slider-dark-4.png
│   │   │   │       ├── slider-dark-5.png
│   │   │   │       ├── slider-dark-6.png
│   │   │   │       ├── slider-dark-7.png
│   │   │   │       ├── slider-dark-8.png
│   │   │   │       ├── slider-light-1.png
│   │   │   │       ├── slider-light-2.png
│   │   │   │       ├── slider-light-3.png
│   │   │   │       ├── slider-light-4.png
│   │   │   │       ├── slider-light-5.png
│   │   │   │       ├── slider-light-6.png
│   │   │   │       ├── slider-light-7.png
│   │   │   │       └── slider-light-8.png
│   │   │   ├── logo-dark.svg
│   │   │   ├── logo.svg
│   │   │   ├── maintenance
│   │   │   │   ├── 500-error.svg
│   │   │   │   ├── empty-dark.svg
│   │   │   │   ├── empty.svg
│   │   │   │   ├── img-bg-grid-dark.svg
│   │   │   │   ├── img-bg-grid.svg
│   │   │   │   ├── img-bg-parts.svg
│   │   │   │   ├── img-build.svg
│   │   │   │   ├── img-ct-dark-logo.png
│   │   │   │   ├── img-ct-light-logo.png
│   │   │   │   ├── img-error-bg-dark.svg
│   │   │   │   ├── img-error-bg.svg
│   │   │   │   ├── img-error-blue.svg
│   │   │   │   ├── img-error-purple.svg
│   │   │   │   ├── img-error-text.svg
│   │   │   │   ├── img-soon-2.svg
│   │   │   │   ├── img-soon-3.svg
│   │   │   │   ├── img-soon-4.svg
│   │   │   │   ├── img-soon-5.svg
│   │   │   │   ├── img-soon-6.svg
│   │   │   │   ├── img-soon-7.svg
│   │   │   │   ├── img-soon-8.svg
│   │   │   │   ├── img-soon-bg-grid-dark.svg
│   │   │   │   ├── img-soon-bg-grid.svg
│   │   │   │   ├── img-soon-bg.svg
│   │   │   │   ├── img-soon-block.svg
│   │   │   │   ├── img-soon-blue-block.svg
│   │   │   │   ├── img-soon-grid-dark.svg
│   │   │   │   ├── img-soon-grid.svg
│   │   │   │   └── img-soon-purple-block.svg
│   │   │   ├── pages
│   │   │   │   ├── card-discover.png
│   │   │   │   ├── card-master.png
│   │   │   │   ├── card-visa.png
│   │   │   │   ├── img-catalog1.png
│   │   │   │   ├── img-catalog2.png
│   │   │   │   └── img-catalog3.png
│   │   │   ├── upload
│   │   │   │   └── upload.svg
│   │   │   ├── users
│   │   │   │   ├── avatar-1.png
│   │   │   │   ├── avatar-10.png
│   │   │   │   ├── avatar-11.png
│   │   │   │   ├── avatar-12.png
│   │   │   │   ├── avatar-2.png
│   │   │   │   ├── avatar-3.png
│   │   │   │   ├── avatar-4.png
│   │   │   │   ├── avatar-5.png
│   │   │   │   ├── avatar-6.png
│   │   │   │   ├── avatar-7.png
│   │   │   │   ├── avatar-8.png
│   │   │   │   ├── avatar-9.png
│   │   │   │   ├── img-user.png
│   │   │   │   ├── profile.png
│   │   │   │   └── user-round.svg
│   │   │   └── widget
│   │   │       ├── australia.jpg
│   │   │       ├── brazil.jpg
│   │   │       ├── dashboard-1.jpg
│   │   │       ├── dashboard-2.jpg
│   │   │       ├── germany.jpg
│   │   │       ├── phone-1.jpg
│   │   │       ├── phone-2.jpg
│   │   │       ├── phone-3.jpg
│   │   │       ├── phone-4.jpg
│   │   │       ├── prod1.jpg
│   │   │       ├── prod2.jpg
│   │   │       ├── prod3.jpg
│   │   │       ├── prod4.jpg
│   │   │       ├── uk.jpg
│   │   │       └── usa.jpg
│   │   └── scss
│   │       ├── _liquidation-bars.scss
│   │       ├── _sonic-dashboard.scss
│   │       ├── _sonic-header.scss
│   │       ├── _sonic-themes.scss
│   │       ├── _sonic-titles.scss
│   │       ├── _theme1.module.scss
│   │       ├── _theme2.module.scss
│   │       ├── _theme3.module.scss
│   │       ├── _theme4.module.scss
│   │       ├── _theme5.module.scss
│   │       ├── _theme6.module.scss
│   │       ├── _themes-vars.module.scss
│   │       ├── index.scss
│   │       ├── scrollbar.scss
│   │       ├── style.scss
│   │       └── yet-another-react-lightbox.scss
│   ├── components
│   │   ├── AppGrid.jsx
│   │   ├── AssetLogo.jsx
│   │   ├── CompositionPieCard
│   │   │   └── CompositionPieCard.jsx
│   │   ├── MarketMovementCard.jsx
│   │   ├── PerformanceGraphCard
│   │   │   ├── PerformanceGraphCard.jsx
│   │   │   └── chart-data
│   │   │       └── market-share-area-chart.jsx
│   │   ├── PortfolioSessionCard
│   │   │   └── PortfolioSessionCard.jsx
│   │   ├── PositionListCard
│   │   │   └── PositionListCard.jsx
│   │   ├── PositionPieCard
│   │   │   └── PositionPieCard.jsx
│   │   ├── ProfitRiskHeaderBadges.jsx
│   │   ├── StatusRail
│   │   │   ├── DashboardToggle.jsx
│   │   │   ├── OperationsBar.jsx
│   │   │   ├── PortfolioBar.jsx
│   │   │   ├── StatCard.jsx
│   │   │   ├── StatusRail.jsx
│   │   │   └── cardData.jsx
│   │   ├── TraderListCard
│   │   │   └── TraderListCard.jsx
│   │   ├── dashboard-grid
│   │   │   ├── DashboardGrid.jsx
│   │   │   ├── GridSection.jsx
│   │   │   ├── GridSlot.jsx
│   │   │   └── registerWidget.js
│   │   ├── old
│   │   │   ├── DashboardToggle.jsx
│   │   │   ├── OperationsBar.jsx
│   │   │   ├── PortfolioBar.jsx
│   │   │   └── StatCard.jsx
│   │   ├── shared
│   │   │   └── Currency.jsx
│   │   └── wallets
│   │       └── VerifiedCells.jsx
│   ├── config.js
│   ├── contexts
│   │   ├── AWSCognitoContext.jsx
│   │   ├── Auth0Context.jsx
│   │   ├── ConfigContext.jsx
│   │   ├── FirebaseContext.jsx
│   │   ├── JWTContext.jsx
│   │   └── SupabaseContext.jsx
│   ├── data
│   │   └── wallets.js
│   ├── hedge-report
│   │   ├── App.tsx
│   │   ├── api
│   │   │   └── hooks.ts
│   │   ├── components
│   │   │   ├── HedgeEvaluator.tsx
│   │   │   └── PositionsTable.tsx
│   │   ├── main.tsx
│   │   ├── pages
│   │   │   └── HedgeReportPage.tsx
│   │   ├── styles
│   │   │   ├── hedge_labs.css
│   │   │   ├── hedge_report.css
│   │   │   └── sonic_themes.css
│   │   └── types
│   │       └── position.ts
│   ├── hooks
│   │   ├── useAuth.js
│   │   ├── useConfig.js
│   │   ├── useLocalStorage.js
│   │   ├── useMenuCollapse.js
│   │   ├── useRunSonicMonitor.js
│   │   ├── useScriptRef.js
│   │   ├── useSonicStatusPolling.js
│   │   └── useXCom.js
│   ├── index.jsx
│   ├── layout
│   │   ├── Customization
│   │   │   ├── BorderRadius.jsx
│   │   │   ├── BoxContainer.jsx
│   │   │   ├── FontFamily.jsx
│   │   │   ├── InputFilled.jsx
│   │   │   ├── Layout.jsx
│   │   │   ├── MenuOrientation.jsx
│   │   │   ├── PresetColor.jsx
│   │   │   ├── SidebarDrawer.jsx
│   │   │   ├── ThemeMode.jsx
│   │   │   └── index.jsx
│   │   ├── MainLayout
│   │   │   ├── Footer.jsx
│   │   │   ├── Header
│   │   │   │   ├── CycloneRunSection
│   │   │   │   │   ├── CycloneRunSection.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── FullScreenSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── LocalizationSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── MegaMenuSection
│   │   │   │   │   ├── Banner.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── MobileSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── NotificationSection
│   │   │   │   │   ├── NotificationList.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── SearchSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── SettingsSection
│   │   │   │   │   ├── UpgradePlanCard.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── ThemeModeSection
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── TimerSection
│   │   │   │   │   ├── DonutCountdown.jsx
│   │   │   │   │   └── TimerSection.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── HorizontalBar.jsx
│   │   │   ├── LogoSection
│   │   │   │   └── index.jsx
│   │   │   ├── MainContentStyled.js
│   │   │   ├── MenuList
│   │   │   │   ├── NavCollapse
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── NavGroup
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── NavItem
│   │   │   │   │   └── index.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── Sidebar
│   │   │   │   ├── MenuCard
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── MiniDrawerStyled.jsx
│   │   │   │   └── index.jsx
│   │   │   └── index.jsx
│   │   ├── MinimalLayout
│   │   │   └── index.jsx
│   │   ├── NavMotion.jsx
│   │   └── NavigationScroll.jsx
│   ├── lib
│   │   └── api
│   │       └── sonicClient.ts
│   ├── menu-items
│   │   ├── alert-thresholds.js
│   │   ├── analytics.js
│   │   ├── dashboard-default.js
│   │   ├── index.js
│   │   ├── kanban.js
│   │   ├── monitor-manager.js
│   │   ├── overview.js
│   │   ├── pages.js
│   │   ├── positions.js
│   │   ├── sonic-labs.js
│   │   ├── sonic.js
│   │   ├── traderFactory.js
│   │   ├── traderShop.js
│   │   └── wallet-manager.js
│   ├── reportWebVitals.js
│   ├── routes
│   │   ├── AuthenticationRoutes.jsx
│   │   ├── ErrorBoundary.jsx
│   │   ├── LoginRoutes.jsx
│   │   ├── MainRoutes.jsx
│   │   ├── TraderShopRoutes.jsx
│   │   └── index.jsx
│   ├── serviceWorker.jsx
│   ├── store
│   │   ├── accountReducer.js
│   │   ├── actions.js
│   │   ├── constant.js
│   │   ├── index.js
│   │   ├── reducer.js
│   │   └── slices
│   │       ├── alertThresholds.js
│   │       ├── kanban.js
│   │       └── snackbar.js
│   ├── tailwind.css
│   ├── themes
│   │   ├── compStyleOverride.jsx
│   │   ├── index.jsx
│   │   ├── overrides
│   │   │   ├── Chip.jsx
│   │   │   └── index.js
│   │   ├── palette.jsx
│   │   ├── shadows.jsx
│   │   └── typography.jsx
│   ├── ui-component
│   │   ├── Loadable.jsx
│   │   ├── Loader.jsx
│   │   ├── Locales.jsx
│   │   ├── Logo.jsx
│   │   ├── RTLLayout.jsx
│   │   ├── cards
│   │   │   ├── AnalyticsChartCard.jsx
│   │   │   ├── AttachmentCard.jsx
│   │   │   ├── AuthFooter.jsx
│   │   │   ├── AuthSlider.jsx
│   │   │   ├── BackgroundPattern1.jsx
│   │   │   ├── BackgroundPattern2.jsx
│   │   │   ├── BillCard.jsx
│   │   │   ├── CardSecondaryAction.jsx
│   │   │   ├── ContactCard.jsx
│   │   │   ├── ContactList.jsx
│   │   │   ├── FloatingCart.jsx
│   │   │   ├── FollowerCard.jsx
│   │   │   ├── FriendRequestCard.jsx
│   │   │   ├── FriendsCard.jsx
│   │   │   ├── FullWidthPaper.jsx
│   │   │   ├── GalleryCard.jsx
│   │   │   ├── HoverDataCard.jsx
│   │   │   ├── HoverSocialCard.jsx
│   │   │   ├── IconNumberCard.jsx
│   │   │   ├── MainCard.jsx
│   │   │   ├── ProductCard.jsx
│   │   │   ├── ProductReview.jsx
│   │   │   ├── ReportCard.jsx
│   │   │   ├── RevenueCard.jsx
│   │   │   ├── RoundIconCard.jsx
│   │   │   ├── SalesLineChartCard.jsx
│   │   │   ├── SeoChartCard.jsx
│   │   │   ├── SideIconCard.jsx
│   │   │   ├── Skeleton
│   │   │   │   ├── EarningCard.jsx
│   │   │   │   ├── ImagePlaceholder.jsx
│   │   │   │   ├── PopularCard.jsx
│   │   │   │   ├── ProductPlaceholder.jsx
│   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   └── TotalIncomeCard.jsx
│   │   │   ├── SubCard.jsx
│   │   │   ├── TotalIncomeDarkCard.jsx
│   │   │   ├── TotalIncomeLightCard.jsx
│   │   │   ├── TotalLineChartCard.jsx
│   │   │   ├── TotalValueCard.jsx
│   │   │   ├── UserCountCard.jsx
│   │   │   ├── UserDetailsCard.jsx
│   │   │   ├── UserProfileCard.jsx
│   │   │   ├── UserSimpleCard.jsx
│   │   │   ├── ValueToCollateralChartCard.jsx
│   │   │   ├── charts
│   │   │   │   └── ValueToCollateralChartCard.jsx
│   │   │   └── positions
│   │   │       └── PositionsTableCard.jsx
│   │   ├── containers
│   │   │   └── DashRowContainer.jsx
│   │   ├── extended
│   │   │   ├── Accordion.jsx
│   │   │   ├── AnimateButton.jsx
│   │   │   ├── AppBar.jsx
│   │   │   ├── Avatar.jsx
│   │   │   ├── Breadcrumbs.jsx
│   │   │   ├── Form
│   │   │   │   ├── FormControl.jsx
│   │   │   │   ├── FormControlSelect.jsx
│   │   │   │   └── InputLabel.jsx
│   │   │   ├── ImageList.jsx
│   │   │   ├── Snackbar.jsx
│   │   │   ├── Transitions.jsx
│   │   │   └── notistack
│   │   │       ├── ColorVariants.jsx
│   │   │       ├── CustomComponent.jsx
│   │   │       ├── Dense.jsx
│   │   │       ├── DismissSnackBar.jsx
│   │   │       ├── HideDuration.jsx
│   │   │       ├── IconVariants.jsx
│   │   │       ├── MaxSnackbar.jsx
│   │   │       ├── PositioningSnackbar.jsx
│   │   │       ├── PreventDuplicate.jsx
│   │   │       ├── SnackBarAction.jsx
│   │   │       ├── TransitionBar.jsx
│   │   │       └── index.jsx
│   │   ├── fun
│   │   │   └── FunCard.jsx
│   │   ├── liquidation
│   │   │   ├── LiqRow.jsx
│   │   │   └── LiquidationBars.jsx
│   │   ├── rails
│   │   │   └── StatusRail.jsx
│   │   ├── status-rail
│   │   │   ├── StatusCard.jsx
│   │   │   ├── StatusRail.jsx
│   │   │   ├── cardData.js
│   │   │   ├── cardData.jsx
│   │   │   └── statusRail.scss
│   │   ├── third-party
│   │   │   ├── Notistack.jsx
│   │   │   └── dropzone
│   │   │       ├── Avatar.jsx
│   │   │       ├── FilePreview.jsx
│   │   │       ├── MultiFile.jsx
│   │   │       ├── PlaceHolderContent.jsx
│   │   │       ├── RejectionFile.jsx
│   │   │       └── SingleFile.jsx
│   │   ├── thresholds
│   │   │   ├── CooldownTable.jsx
│   │   │   └── ThresholdTable.jsx
│   │   └── wallet
│   │       ├── WalletFormModal.jsx
│   │       ├── WalletPieCard.jsx
│   │       └── WalletTable.jsx
│   ├── utils
│   │   ├── axios.js
│   │   ├── getDropzoneData.js
│   │   ├── getImageUrl.js
│   │   ├── hedgeColors.js
│   │   ├── locales
│   │   │   ├── en.json
│   │   │   ├── fr.json
│   │   │   ├── ro.json
│   │   │   └── zh.json
│   │   ├── password-strength.js
│   │   └── route-guard
│   │       ├── AuthGuard.jsx
│   │       └── GuestGuard.jsx
│   ├── views
│   │   ├── alertThresholds
│   │   │   ├── AddThresholdDialog.jsx
│   │   │   ├── AlertThresholdsPage.jsx
│   │   │   ├── ThresholdsTable.jsx
│   │   │   ├── icons.jsx
│   │   │   └── index.jsx
│   │   ├── dashboard
│   │   │   ├── Analytics
│   │   │   │   ├── index - Copy (2).jsx
│   │   │   │   ├── index - Copy.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── CompositionPieCard.jsx
│   │   │   ├── Default
│   │   │   │   ├── BajajAreaChartCard.jsx
│   │   │   │   ├── EarningCard.jsx
│   │   │   │   ├── PopularCard.jsx
│   │   │   │   ├── TotalGrowthBarChart.jsx
│   │   │   │   ├── TotalOrderLineChartCard.jsx
│   │   │   │   ├── chart-data
│   │   │   │   │   ├── bajaj-area-chart.jsx
│   │   │   │   │   ├── total-growth-bar-chart.jsx
│   │   │   │   │   ├── total-order-month-line-chart.jsx
│   │   │   │   │   └── total-order-year-line-chart.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── PerformanceGraphCard.jsx
│   │   │   ├── PositionListCard.jsx
│   │   │   ├── ProfitRiskHeaderBadges.jsx
│   │   │   ├── TraderListCard.jsx
│   │   │   ├── VerticalMonitorSummaryCard.jsx
│   │   │   ├── analytics-wireframe.json
│   │   │   ├── chart-data
│   │   │   │   └── market-share-area-chart.jsx
│   │   │   └── market-share-area-chart.jsx
│   │   ├── debug
│   │   │   └── DatabaseViewer.jsx
│   │   ├── forms
│   │   │   ├── chart
│   │   │   │   ├── Apexchart
│   │   │   │   │   ├── ApexAreaChart.jsx
│   │   │   │   │   ├── ApexBarChart.jsx
│   │   │   │   │   ├── ApexColumnChart.jsx
│   │   │   │   │   ├── ApexLineChart.jsx
│   │   │   │   │   ├── ApexMixedChart.jsx
│   │   │   │   │   ├── ApexPieChart.jsx
│   │   │   │   │   ├── ApexPolarChart.jsx
│   │   │   │   │   ├── ApexRedialChart.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── OrgChart
│   │   │   │       ├── Card.jsx
│   │   │   │       ├── DataCard.jsx
│   │   │   │       ├── LinkedIn.jsx
│   │   │   │       ├── MeetIcon.jsx
│   │   │   │       ├── SkypeIcon.jsx
│   │   │   │       └── index.jsx
│   │   │   ├── components
│   │   │   │   ├── AutoComplete.jsx
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Checkbox.jsx
│   │   │   │   ├── DateTime
│   │   │   │   │   ├── CustomDateTime.jsx
│   │   │   │   │   ├── LandscapeDateTime.jsx
│   │   │   │   │   ├── ViewRendererDateTime.jsx
│   │   │   │   │   ├── ViewsDateTimePicker.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Radio.jsx
│   │   │   │   ├── Slider
│   │   │   │   │   ├── BasicSlider.jsx
│   │   │   │   │   ├── DisableSlider.jsx
│   │   │   │   │   ├── LabelSlider.jsx
│   │   │   │   │   ├── PopupSlider.jsx
│   │   │   │   │   ├── StepSlider.jsx
│   │   │   │   │   ├── VerticalSlider.jsx
│   │   │   │   │   ├── VolumeSlider.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Switch.jsx
│   │   │   │   └── TextField.jsx
│   │   │   ├── data-grid
│   │   │   │   ├── ColumnGroups
│   │   │   │   │   ├── BasicColumnGroup.jsx
│   │   │   │   │   ├── CustomColumnGroup.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── ColumnMenu
│   │   │   │   │   ├── AddMenuItem.jsx
│   │   │   │   │   ├── ColumnMenu.jsx
│   │   │   │   │   ├── CustomMenu.jsx
│   │   │   │   │   ├── DisableMenu.jsx
│   │   │   │   │   ├── HideMenuItem.jsx
│   │   │   │   │   ├── OverrideMenu.jsx
│   │   │   │   │   ├── ReorderingMenu.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── ColumnVirtualization
│   │   │   │   │   ├── Virtualization.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── ColumnVisibility
│   │   │   │   │   ├── ControlledVisibility.jsx
│   │   │   │   │   ├── InitializeColumnVisibility.jsx
│   │   │   │   │   ├── VisibilityPanel.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── DataGridBasic
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── InLineEditing
│   │   │   │   │   ├── AutoStop.jsx
│   │   │   │   │   ├── ConfirmationSave.jsx
│   │   │   │   │   ├── Controlled.jsx
│   │   │   │   │   ├── CustomEdit.jsx
│   │   │   │   │   ├── DisableEditing.jsx
│   │   │   │   │   ├── EditableColumn.jsx
│   │   │   │   │   ├── EditableRow.jsx
│   │   │   │   │   ├── EditingEvents.jsx
│   │   │   │   │   ├── FullFeatured.jsx
│   │   │   │   │   ├── ParserSetter.jsx
│   │   │   │   │   ├── ServerValidation.jsx
│   │   │   │   │   ├── Validation.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── QuickFilter
│   │   │   │   │   ├── CustomFilter.jsx
│   │   │   │   │   ├── ExcludeHiddenColumns.jsx
│   │   │   │   │   ├── Initialize.jsx
│   │   │   │   │   ├── ParsingValues.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── SaveRestoreState
│   │   │   │       ├── InitialState.jsx
│   │   │   │       ├── UseGridSelector.jsx
│   │   │   │       └── index.jsx
│   │   │   ├── forms-validation
│   │   │   │   ├── AutocompleteForms.jsx
│   │   │   │   ├── CheckboxForms.jsx
│   │   │   │   ├── InstantFeedback.jsx
│   │   │   │   ├── LoginForms.jsx
│   │   │   │   ├── RadioGroupForms.jsx
│   │   │   │   ├── SelectForms.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── forms-wizard
│   │   │   │   ├── BasicWizard
│   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   ├── Review.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── ValidationWizard
│   │   │   │   │   ├── AddressForm.jsx
│   │   │   │   │   ├── PaymentForm.jsx
│   │   │   │   │   ├── Review.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── layouts
│   │   │   │   ├── ActionBar.jsx
│   │   │   │   ├── Layouts.jsx
│   │   │   │   ├── MultiColumnForms.jsx
│   │   │   │   └── StickyActionBar.jsx
│   │   │   ├── plugins
│   │   │   │   ├── AutoComplete.jsx
│   │   │   │   ├── Clipboard.jsx
│   │   │   │   ├── Dropzone.jsx
│   │   │   │   ├── Editor.jsx
│   │   │   │   ├── Mask.jsx
│   │   │   │   ├── Modal
│   │   │   │   │   ├── ServerModal.jsx
│   │   │   │   │   ├── SimpleModal.jsx
│   │   │   │   │   └── index.jsx
│   │   │   │   ├── Recaptcha.jsx
│   │   │   │   └── Tooltip.jsx
│   │   │   └── tables
│   │   │       ├── TableBasic.jsx
│   │   │       ├── TableCollapsible.jsx
│   │   │       ├── TableData.jsx
│   │   │       ├── TableDense.jsx
│   │   │       ├── TableEnhanced.jsx
│   │   │       ├── TableExports.jsx
│   │   │       ├── TableStickyHead.jsx
│   │   │       └── TablesCustomized.jsx
│   │   ├── hedgeReport
│   │   │   ├── HedgeReportPage.jsx
│   │   │   └── index.jsx
│   │   ├── kanban
│   │   │   ├── Backlogs
│   │   │   │   ├── AddItem.jsx
│   │   │   │   ├── AddStory.jsx
│   │   │   │   ├── AddStoryComment.jsx
│   │   │   │   ├── AlertStoryDelete.jsx
│   │   │   │   ├── EditStory.jsx
│   │   │   │   ├── Items.jsx
│   │   │   │   ├── StoryComment.jsx
│   │   │   │   ├── UserStory.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── Board
│   │   │   │   ├── AddColumn.jsx
│   │   │   │   ├── AddItem.jsx
│   │   │   │   ├── AddItemComment.jsx
│   │   │   │   ├── AlertColumnDelete.jsx
│   │   │   │   ├── AlertItemDelete.jsx
│   │   │   │   ├── Columns.jsx
│   │   │   │   ├── EditColumn.jsx
│   │   │   │   ├── EditItem.jsx
│   │   │   │   ├── ItemComment.jsx
│   │   │   │   ├── ItemDetails.jsx
│   │   │   │   ├── Items.jsx
│   │   │   │   └── index.jsx
│   │   │   └── index.jsx
│   │   ├── monitorManager
│   │   │   ├── LiquidationMonitorCard.jsx
│   │   │   ├── MarketMonitorCard.jsx
│   │   │   ├── MonitorManager.jsx
│   │   │   ├── MonitorUpdateBar.jsx
│   │   │   ├── ProfitMonitorCard.jsx
│   │   │   └── SonicMonitorCard.jsx
│   │   ├── overview
│   │   │   └── index.jsx
│   │   ├── pages
│   │   │   ├── authentication
│   │   │   │   ├── AuthCardWrapper.jsx
│   │   │   │   ├── AuthWrapper1.jsx
│   │   │   │   ├── AuthWrapper2.jsx
│   │   │   │   ├── CheckMail.jsx
│   │   │   │   ├── CodeVerification.jsx
│   │   │   │   ├── ForgotPassword.jsx
│   │   │   │   ├── Login.jsx
│   │   │   │   ├── LoginProvider.jsx
│   │   │   │   ├── Register.jsx
│   │   │   │   ├── ResetPassword.jsx
│   │   │   │   ├── ViewOnlyAlert.jsx
│   │   │   │   ├── auth0
│   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   ├── aws
│   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   ├── firebase
│   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   ├── AuthResetPassword.jsx
│   │   │   │   │   └── FirebaseSocial.jsx
│   │   │   │   ├── jwt
│   │   │   │   │   ├── AuthCodeVerification.jsx
│   │   │   │   │   ├── AuthForgotPassword.jsx
│   │   │   │   │   ├── AuthLogin.jsx
│   │   │   │   │   ├── AuthRegister.jsx
│   │   │   │   │   └── AuthResetPassword.jsx
│   │   │   │   └── supabase
│   │   │   │       ├── AuthCodeVerification.jsx
│   │   │   │       ├── AuthForgotPassword.jsx
│   │   │   │       ├── AuthLogin.jsx
│   │   │   │       ├── AuthRegister.jsx
│   │   │   │       └── AuthResetPassword.jsx
│   │   │   └── maintenance
│   │   │       ├── ComingSoon
│   │   │       │   ├── ComingSoon1
│   │   │       │   │   ├── MailerSubscriber.jsx
│   │   │       │   │   ├── Slider.jsx
│   │   │       │   │   └── index.jsx
│   │   │       │   └── ComingSoon2.jsx
│   │   │       ├── Error.jsx
│   │   │       ├── Error500.jsx
│   │   │       ├── Forbidden.jsx
│   │   │       └── UnderConstruction.jsx
│   │   ├── positions
│   │   │   ├── LiquidationBarsCard.jsx
│   │   │   ├── PositionTableCard.jsx
│   │   │   ├── PositionsPage.jsx
│   │   │   ├── SidePanelWidthSlider.jsx
│   │   │   └── index.jsx
│   │   ├── sonic
│   │   │   ├── index.jsx
│   │   │   └── index_BU.jsx
│   │   ├── sonicLabs
│   │   │   ├── SonicLabsPage.jsx
│   │   │   └── index.jsx
│   │   ├── traderFactory
│   │   │   ├── TraderBar.jsx
│   │   │   ├── TraderCard.css
│   │   │   ├── TraderCard.jsx
│   │   │   └── TraderFactoryPage.jsx
│   │   ├── traderShop
│   │   │   ├── QuickImportStarWars.jsx
│   │   │   ├── TraderEnhancedTable.jsx
│   │   │   ├── TraderFormDrawer.jsx
│   │   │   ├── TraderShopList.jsx
│   │   │   ├── hooks.js
│   │   │   ├── index.jsx
│   │   │   └── sampleTraders.json
│   │   ├── utilities
│   │   │   ├── Animation.jsx
│   │   │   ├── Color.jsx
│   │   │   ├── Grid
│   │   │   │   ├── AutoGrid.jsx
│   │   │   │   ├── BasicGrid.jsx
│   │   │   │   ├── ColumnsGrid.jsx
│   │   │   │   ├── ComplexGrid.jsx
│   │   │   │   ├── GridItem.jsx
│   │   │   │   ├── MultipleBreakPoints.jsx
│   │   │   │   ├── NestedGrid.jsx
│   │   │   │   ├── SpacingGrid.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── Shadow.jsx
│   │   │   └── Typography.jsx
│   │   ├── wallet
│   │   │   ├── BalanceBreakdownCard.jsx
│   │   │   └── WalletManager.jsx
│   │   ├── widget
│   │   │   ├── Chart
│   │   │   │   ├── ConversionsChartCard.jsx
│   │   │   │   ├── MarketSaleChartCard.jsx
│   │   │   │   ├── RevenueChartCard.jsx
│   │   │   │   ├── SatisfactionChartCard.jsx
│   │   │   │   ├── chart-data
│   │   │   │   │   ├── conversions-chart.jsx
│   │   │   │   │   ├── index.jsx
│   │   │   │   │   ├── market-sale-chart.jsx
│   │   │   │   │   ├── percentage-chart.jsx
│   │   │   │   │   ├── revenue-chart.jsx
│   │   │   │   │   ├── sale-chart-1.jsx
│   │   │   │   │   ├── satisfaction-chart.jsx
│   │   │   │   │   ├── seo-chart-1.jsx
│   │   │   │   │   ├── seo-chart-2.jsx
│   │   │   │   │   ├── seo-chart-3.jsx
│   │   │   │   │   ├── seo-chart-4.jsx
│   │   │   │   │   ├── seo-chart-5.jsx
│   │   │   │   │   ├── seo-chart-6.jsx
│   │   │   │   │   ├── seo-chart-7.jsx
│   │   │   │   │   ├── seo-chart-8.jsx
│   │   │   │   │   ├── seo-chart-9.jsx
│   │   │   │   │   ├── total-value-graph-1.jsx
│   │   │   │   │   ├── total-value-graph-2.jsx
│   │   │   │   │   └── total-value-graph-3.jsx
│   │   │   │   └── index.jsx
│   │   │   ├── Data
│   │   │   │   ├── ActiveTickets.jsx
│   │   │   │   ├── ApplicationSales.jsx
│   │   │   │   ├── FeedsCard.jsx
│   │   │   │   ├── IncomingRequests.jsx
│   │   │   │   ├── LatestCustomers.jsx
│   │   │   │   ├── LatestMessages.jsx
│   │   │   │   ├── LatestOrder.jsx
│   │   │   │   ├── LatestPosts.jsx
│   │   │   │   ├── NewCustomers.jsx
│   │   │   │   ├── ProductSales.jsx
│   │   │   │   ├── ProjectTable.jsx
│   │   │   │   ├── RecentTickets.jsx
│   │   │   │   ├── TasksCard.jsx
│   │   │   │   ├── TeamMembers.jsx
│   │   │   │   ├── ToDoList.jsx
│   │   │   │   ├── TotalRevenue.jsx
│   │   │   │   ├── TrafficSources.jsx
│   │   │   │   ├── UserActivity.jsx
│   │   │   │   └── index.jsx
│   │   │   └── Statistics
│   │   │       ├── CustomerSatisfactionCard.jsx
│   │   │       ├── IconGridCard.jsx
│   │   │       ├── ProjectTaskCard.jsx
│   │   │       ├── WeatherCard.jsx
│   │   │       └── index.jsx
│   │   └── xcomSettings
│   │       ├── XComSettings.jsx
│   │       └── components
│   │           └── ProviderAccordion.jsx
│   └── vite-env.d.js
├── static
│   ├── images
│   │   ├── Wally.png
│   │   ├── __init__.py
│   │   ├── aave.jpg
│   │   ├── alert_wall.jpg
│   │   ├── boba_icon.jpg
│   │   ├── bobavault.jpg
│   │   ├── btc_logo.png
│   │   ├── bubba_icon.png
│   │   ├── c3po_icon.jpg
│   │   ├── c3povault.jpg
│   │   ├── chewbaccavault.jpg
│   │   ├── chewie_icon.jpg
│   │   ├── cityscape3.jpg
│   │   ├── container_wallpaper.jpg
│   │   ├── corner_icon.jpg
│   │   ├── corner_logo_owl.jpg
│   │   ├── corner_logos.jpg
│   │   ├── crypto_icon.jpg
│   │   ├── crypto_iconz.png
│   │   ├── database_wall.jpg
│   │   ├── error.png
│   │   ├── eth_logo.png
│   │   ├── jabba_icon.jpg
│   │   ├── jabba_icon.png
│   │   ├── jabbavault.jpg
│   │   ├── jupiter.jpg
│   │   ├── lando_icon.jpg
│   │   ├── landovault.jpg
│   │   ├── lawyer.jpg
│   │   ├── leia_icon.jpg
│   │   ├── leiavault.jpg
│   │   ├── logo.png
│   │   ├── logo2.png
│   │   ├── luke_icon.jpg
│   │   ├── lukevault.jpg
│   │   ├── monitor_wallpaper.jpg
│   │   ├── obi_icon.jpg
│   │   ├── obivault.jpg
│   │   ├── palpatine_icon.jpg
│   │   ├── palpatinevault.jpg
│   │   ├── r2d2_icon.jpg
│   │   ├── r2vault.jpg
│   │   ├── raydium.jpg
│   │   ├── sol_logo.png
│   │   ├── sonars.png
│   │   ├── sonic.png
│   │   ├── sonic_burst.png
│   │   ├── sonic_title.png
│   │   ├── space_wall4.jpg
│   │   ├── super_sonic.png
│   │   ├── sys_config_wall.jpg
│   │   ├── trader_wallpaper.jpg
│   │   ├── twilio.png
│   │   ├── unknown.png
│   │   ├── unknown_wallet.jpg
│   │   ├── vader_icon.jpg
│   │   ├── vadervault.jpg
│   │   ├── wallpaper2.jpg
│   │   ├── wallpaper2.png
│   │   ├── wallpaper4.jpg
│   │   ├── wallpaper5.jpg
│   │   ├── wallpaper6.jpg
│   │   ├── wallpaper_green.png
│   │   ├── wallpaper_grey_blue.jpg
│   │   ├── wallpapersden.jpg
│   │   ├── wally2.png
│   │   ├── yoda_icon.jpg
│   │   └── yodavault.jpg
│   └── sounds
│       ├── alert_liq.mp3
│       ├── death_spiral.mp3
│       ├── error.mp3
│       ├── fail.mp3
│       ├── level-up.mp3
│       ├── message_alert.mp3
│       ├── profit_alert.mp3
│       └── web_station_startup.mp3
├── tailwind.config.js
├── tsconfig.json
├── vite.config.mjs
└── yarn.lock

158 directories, 807 files
```

The `alertThresholds` folder implements the **Alert Thresholds** page available
under the `/alert-thresholds` route. The `traderShop` folder provides the
**Trader Shop** at `/trader-shop`. The `hedge-report` directory contains a
standalone hedging report tool written in TypeScript.

The frontend depends on **Tailwind CSS** for styling. Install dependencies and
run the unit tests with:

```bash
npm install
npm test
```
