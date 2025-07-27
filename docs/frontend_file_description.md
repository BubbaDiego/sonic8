# Frontend File Descriptions

The notes below summarize the purpose of key files and directories under `frontend/`.

### Root Level
- **.env** / **.env.qa** – Example environment files used during development.
- **.gitignore** – Patterns for files ignored by Git.
- **.prettierrc** – Code formatting rules for Prettier.
- **.yarnrc.yml** – Yarn configuration file.
- **eslint.config.mjs** – ESLint setup for linting the React codebase.
- **favicon.svg** – Default browser tab icon.
- **index.html** – Entry HTML page used by Vite.
- **jsconfig.json** / **jsconfig.node.json** – Editor settings for path resolution.
- **package.json** / **package-lock.json** – NPM dependencies and lock file.
- **vite.config.mjs** – Vite build and dev server configuration.
- **yarn.lock** – Lock file for Yarn installs.
- **src/** – Main React application source code.

### `src/`
- **App.jsx** – Root React component mounting routes and context providers.
- **api/** – Simple wrappers around backend API endpoints (e.g., cyclone, menu, products).
  - **monitorStatus.js** – Provides the `useGetMonitorStatus` hook for retrieving
    the monitor status summary from `/monitor_status/` and a refresh helper.
- **assets/** – SCSS styles and bundled images for the UI.
  - **images/** – Logos and themed illustrations used throughout the site.
  - **scss/** – Theme variables and global styling.
  - **config.js** – Global configuration values for the frontend.
    - Includes the default `ThemeMode` setting. Available modes are `light`,
      `dark`, and `system`.
  - **contexts/** – React context providers for authentication and configuration (Auth0, Firebase, JWT, etc.).
- **hooks/** – Reusable React hooks like `useAuth` and `useConfig`.
- **index.jsx** – Vite entry point rendering `App`.
- **layout/** – Layout components including main and minimal page shells.
- **menu-items/** – Definitions used to build the sidebar navigation menu.
- **reportWebVitals.js** – Vite's performance reporting helper.
- **routes/** – React Router route groupings for authentication and dashboard pages.
- **serviceWorker.jsx** – Register/unregister functions for PWA service worker.
- **store/** – Redux store setup and slice definitions.
  - **slices/** – Reducer logic for features like snackbar notifications.
- **themes/** – Material‑UI theme configuration and overrides.
  - **overrides/** – Component style overrides for the theme.
- **ui-component/** – Shared UI components used across pages (cards, forms, third‑party widgets).
- **utils/** – Helper functions, localization files, and route guards.
  - **locales/** – JSON translation files (en, fr, etc.).
  - **route-guard/** – Higher order components enforcing auth/guest access.
- **views/** – Page level React components organized by domain.
  - **pages/** – Authentication and maintenance pages.
  - **overview/** – Blank page template for new routes.
- **vite-env.d.js** – Type declarations for Vite tooling.
