# 🛠️ Sonic React UI Documentation

---

## 📁 Folder Structure

A straightforward folder structure simplifies navigation:

```
berry-material-react/
├── src
│   ├── api                -> Mock JSON data for apps
│   ├── assets
│   │   ├── image       
│   │   └── scss           -> Theme presets
│   ├── contexts           -> State context for Login & config
│   ├── data               -> Static data
│   ├── hook               -> Custom hooks
│   ├── layout
│   │   ├── Customization
│   │   ├── MainLayout
│   │   ├── MinimalLayout
│   │   ├── SimpleLayout
│   │   ├── NavigationScroll.jsx
│   │   └── NavMotion.jsx
│   ├── menu-items
│   ├── routes
│   ├── store              -> Redux actions, reducers
│   │   └── slices
│   ├── themes             -> App styles/themes
│   ├── ui-component       -> Custom components
│   ├── utils
│   │   ├── locales
│   │   └── route-guard
│   ├── views
│   ├── App.jsx            -> App entry
│   ├── config.jsx         -> Constants & customization
│   └── index.jsx          -> Root file
├── .env
├── eslint.config.mjs
├── .prettierrc
├── jsconfig.json
├── package-lock.json
├── package.json
├── vite.config.mjs
├── README.md
└── yarn.lock
```

---

## 🔄 State Management

### Context API

Used for login methods: Auth0, JWT, Firebase. (`src/contexts/configContext.jsx`)

### Designing Actions

```javascript
export const LOGIN = 'LOGIN';
export const LOGOUT = 'LOGOUT';
export const REGISTER = 'REGISTER';
export const FIREBASE_STATE_CHANGED = 'FIREBASE_STATE_CHANGED';
```

### Reducers

Reducers manage state (`src/store/slice/contact.js`).

---

## 🌐 Multi Language

Supports 'en', 'fr', 'ro', 'zh'. Locale files in `src/utils/locales`. Change default in `src/config.js`:

```javascript
i18n: 'en', // 'en', 'fr', 'ro', 'zh'
```

---

## 🔑 Authentication

Supports JWT (default), Firebase, Auth0, AWS Cognito.

Authentication config (`.env`):

```env
VITE_APP_API_URL=https://mock-data-api-nextjs.vercel.app/
VITE_APP_FIREBASE_API_KEY=
VITE_APP_AWS_POOL_ID=
VITE_APP_AUTH0_CLIENT_ID=
```

---

## 🌐 API Calls

Axios setup (`src/utils/axios.js`):

```javascript
const axiosServices = axios.create({ baseURL: import.meta.env.VITE_APP_API_URL });
```

---

## 🛣️ Routing

Uses `react-router-dom`.

### MainRoutes

Add routes in `src/routes/MainRoutes.jsx`.

### Login as Default

Set login as the default route in `src/routes/index.jsx`.

### Skip Authentication

Comment/uncomment `AuthGuard` in `src/routes/MainRoutes.jsx` to disable/enable auth temporarily.

---

## 🎨 Theme Customization

### Configuration

Edit global settings in `src/config.ts`:
[cyclone_core](../backend/core/cyclone_core)
- layout
- fontFamily
- borderRadius
- mode ('light'/'dark'/'funky')
- presetColor
- language (`i18n`)
- themeDirection ('ltr'/'rtl')
- container layout

### Presets

Change presets via `src/assets/scss/_theme*.module.scss`.

### Style

Theme styles centralized in `src/themes`:

- Colors (`palette.tsx`)
- Typography (`typography.tsx`)
- Overrides (`compStyleOverride.jsx`)
- Shadows (`shadows.tsx`)

### Logo

Update logo (`src/ui-component/Logo.jsx`):

```jsx
import logo from 'assets/images/logo.svg';

const Logo = () => (
  <img src={logo} alt="Sonic" width="100" />
);

export default Logo;
```

---

## 🌱 Get Started with Seed

The Seed version provides a basic structure with minimal files, dependencies, and an overview page to help start projects quickly. Add components from the full version by copying files and resolving paths.

---

## 🧩 Components

Extended MUI Components:

- [Avatar](https://berrydashboard.io/basic/avatar)
- AnimateButton
- [Accordion](https://berrydashboard.io/basic/accordion)
- [Breadcrumbs](https://berrydashboard.io/basic/breadcrumb)
- [Chip](https://berrydashboard.io/basic/chip)
- ImageList
- MainCard
- Transitions
- SubCard

Each component extends standard MUI functionality with additional properties.

---

## 📦 Dependencies

Sonic includes essential dependencies preloaded in `package.json`, simplifying project setup. Dependencies include various MUI libraries, React utilities, form handlers, and more. Development dependencies ensure efficient workflow and code quality management.

---

🎉 **You're all set!** 🎉

