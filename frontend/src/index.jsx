import React from 'react';
import { createRoot } from 'react-dom/client';

import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';

// Keep imports RELATIVE so Vite resolves them.
import App from './App';
import { store, persistor } from './store';
import * as ConfigCtx from './contexts/ConfigContext';

// SCSS bundles (requires "sass" in devDependencies)
import './assets/scss/index.scss';
import './assets/scss/style.scss';
import './assets/scss/_liquidation-bars.scss';
import './index.css';

// map styles
import 'mapbox-gl/dist/mapbox-gl.css';

// google-fonts
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';

import '@fontsource/poppins/400.css';
import '@fontsource/poppins/500.css';
import '@fontsource/poppins/600.css';
import '@fontsource/poppins/700.css';

// CRA leftovers shimmed so import errors don't kill boot
import reportWebVitals from './reportWebVitals';
import * as serviceWorker from './serviceWorker';

// Tiny runtime error overlay so a crash isn't a blank page
function showBootError(err) {
  const el = document.createElement('pre');
  el.style.cssText =
    'position:fixed;inset:0;z-index:99999;margin:0;padding:16px;color:#fff;background:#1b0000;overflow:auto;font:12px/1.4 Menlo,Consolas,monospace;';
  el.textContent = `BOOT ERROR\n\n${(err && (err.stack || err.message)) || String(err)}`;
  document.body.appendChild(el);
}

const ConfigProvider =
  (ConfigCtx && (ConfigCtx.ConfigProvider || ConfigCtx.default)) || React.Fragment;

// Ensure theme asset URLs resolve correctly at runtime
const base = import.meta.env.BASE_URL || '/';
document.documentElement.style.setProperty('--asset-base', base);

try {
  const container = document.getElementById('root');
  if (!container) throw new Error('Missing <div id="root"> in index.html');

  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <Provider store={store}>
        <PersistGate loading={null} persistor={persistor}>
          <ConfigProvider>
            <App />
          </ConfigProvider>
        </PersistGate>
      </Provider>
    </React.StrictMode>
  );
} catch (err) {
  // eslint-disable-next-line no-console
  console.error(err);
  showBootError(err);
}

reportWebVitals();
serviceWorker.unregister();
