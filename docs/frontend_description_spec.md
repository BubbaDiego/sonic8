# Frontend Description Spec

## Repo Map

```txt
frontend/
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
├── vite.config.mjs
├── yarn.lock
├── src
│   ├── SonicReactApp.jsx
│   ├── api/
│   ├── assets/
│   │   ├── images/
│   │   └── scss/
│   ├── config.js
│   ├── contexts/
│   ├── data/
│   ├── hooks/
│   ├── index_sonic.jsx
│   ├── layout/
│   ├── menu-items/
│   ├── metrics/
│   ├── reportWebVitals.js
│   ├── routes/
│   ├── serviceWorker.jsx
│   ├── store/
│   │   └── slices/
│   ├── themes/
│   │   └── overrides/
│   ├── ui-component/
│   │   ├── cards/
│   │   ├── extended/
│   │   └── third-party/
│   ├── utils/
│   │   ├── locales/
│   │   └── route-guard/
│   ├── views/
│   │   ├── application/
│   │   ├── cyclone/
│   │   ├── dashboard/
│   │   ├── forms/
│   │   ├── pages/
│   │   ├── sample-page/
│   │   ├── ui-elements/
│   │   ├── utilities/
│   │   └── widget/
│   └── vite-env.d.js
├── static
│   ├── images/
│   └── sounds/
```

## Folder & File Descriptions

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
- **static/** – Images and sound effects loaded directly by the app.

### `src/`
- **SonicReactApp.jsx** – Application bootstrap component mounting the router and contexts.
- **api/** – Simple wrappers around backend API endpoints (e.g., cyclone, menu, products).
- **assets/** – SCSS styles and bundled images for the UI.
  - **images/** – Logos and themed illustrations used throughout the site.
  - **scss/** – Theme variables and global styling.
- **config.js** – Global configuration values for the frontend.
- **contexts/** – React context providers for authentication and configuration (Auth0, Firebase, JWT, etc.).
- **data/** – Static location data and other seeding information.
- **hooks/** – Reusable React hooks like `useAuth` and `useConfig`.
- **index_sonic.jsx** – Vite entry point rendering `SonicReactApp`.
- **layout/** – Layout components including main dashboard, minimal and simple page shells.
- **menu-items/** – Definitions used to build the sidebar navigation menu.
- **metrics/** – Components for analytics tags and notifications.
- **reportWebVitals.js** – Vite's performance reporting helper.
- **routes/** – React Router route groupings for authentication and dashboard pages.
- **serviceWorker.jsx** – Register/unregister functions for PWA service worker.
- **store/** – Redux store setup and slice definitions.
  - **slices/** – Reducer logic for features like cart, user, and snackbar.
- **themes/** – Material‑UI theme configuration and overrides.
  - **overrides/** – Component style overrides for the theme.
- **ui-component/** – Shared UI components used across pages (cards, forms, third‑party widgets).
- **utils/** – Helper functions, localization files, and route guards.
  - **locales/** – JSON translation files (en, fr, etc.).
  - **route-guard/** – Higher order components enforcing auth/guest access.
- **views/** – Page level React components organized by domain.
  - **application/** – Blog, calendar, chat, and other demo applications.
  - **cyclone/** – Components for running a Cyclone process from the UI.
  - **dashboard/** – Default and Sonic‑specific dashboard widgets.
  - **forms/** – Sample form demos and wizards.
  - **pages/** – Authentication, landing, and misc pages.
  - **sample-page/** – Blank page template for new routes.
  - **ui-elements/** – Material‑UI element showcases.
  - **utilities/** – Misc utilities like color, shadow, and typography samples.
  - **widget/** – Example widget demos and layout pieces.
- **vite-env.d.js** – Type declarations for Vite tooling.

### `static/`
- **images/** – Pre-bundled static images such as logos and character graphics.
- **sounds/** – MP3 sound effects used for notifications and game events.

This document summarizes the structure and purpose of the frontend folder to help navigate key files and directories quickly.
