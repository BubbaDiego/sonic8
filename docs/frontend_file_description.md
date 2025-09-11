# Frontend File Descriptions

The notes below summarize the purpose of key files and directories under `frontend/`.

### Root Level
The root of the React project contains configuration, build tooling and test
files.

- **.env** / **.env.qa** – Example environment files used during development.
- **.gitignore** – Patterns for files ignored by Git.
- **.prettierrc** – Code formatting rules for Prettier.
- **.yarn/** – Yarn installation metadata.
- **.yarnrc.yml** – Yarn configuration file.
- **__tests__/** – Jest unit tests for key components and hooks.
- **babel.config.js** – Babel configuration for the build pipeline.
- **eslint.config.mjs** – ESLint setup for linting the React codebase.
- **favicon.svg** – Default browser tab icon.
- **index.html** – Entry HTML page used by Vite.
- **jest.config.js** – Jest test runner configuration.
- **jsconfig.json** / **jsconfig.node.json** – Editor settings for path resolution.
- **package.json** / **package-lock.json** – NPM dependencies and lock file.
- **postcss.config.js** – Tailwind/PostCSS processing rules.
- **public/** – Static assets copied to the Vite build output.
- **tailwind.config.js** – Tailwind CSS theme configuration.
- **tsconfig.json** – TypeScript configuration.
- **vite.config.mjs** – Vite build and dev server configuration.
- **yarn.lock** – Lock file for Yarn installs.
- **src/** – Main React application source code.

### `src/`
- **App.jsx** – Root React component mounting routes and context providers.
- **api/** – Simple wrappers around backend API endpoints (e.g., cyclone, menu, products).
  - **monitorStatus.js** – Provides the `useGetMonitorStatus` hook for retrieving
    the monitor status summary from `/api/monitor-status/` and a refresh helper.
- **assets/** – SCSS styles, images and other static resources for the UI.
  - **images/** – Logos and themed illustrations used throughout the site.
  - **scss/** – Theme variables and global styling.
- **components/** – Reusable UI building blocks such as cards, graphs and tables.
- **config.js** – Global configuration values for the frontend
  (including default `ThemeMode` settings `light`, `dark` and `funky`).
- **contexts/** – React context providers for authentication and configuration (Auth0, Firebase, JWT, etc.).
- **data/** – Static sample data used by components and tests.
- **hedge-report/** – TypeScript-based hedging report sub‑application.
- **hooks/** – Reusable React hooks like `useAuth` and `useConfig`.
- **index.jsx** – Vite entry point rendering `App`.
- **layout/** – Layout components including main and minimal page shells.
- **lib/** – Domain specific utilities and helper libraries.
- **menu-items/** – Definitions used to build the sidebar navigation menu.
- **reportWebVitals.js** – Vite's performance reporting helper.
- **routes/** – React Router route groupings for authentication and dashboard pages.
- **serviceWorker.jsx** – Register/unregister functions for PWA service worker.
- **store/** – Redux store setup and slice definitions.
  - **slices/** – Reducer logic for features like snackbar notifications.
- **tailwind.css** – Bundled Tailwind styles used by the application.
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
