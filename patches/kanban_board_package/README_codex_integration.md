
# 🏗️ Kanban Board – Integration Guide for Codex

This package delivers **Option B** (interactive local‑state Kanban board) for your Berry‑Material React code‑base.

---

## 1.  Install dependencies

```bash
npm i @dnd-kit/core @dnd-kit/sortable @dnd-kit/modifiers       redux-persist axios-mock-adapter
```

> `redux‑persist` keeps the Kanban slice in **localStorage** so the board “resists” page reloads.  
> `axios-mock-adapter` mocks the `/api/kanban/*` REST routes – no backend needed.

---

## 2.  Copy the files

```
src/__mocks__/kanbanData.js
src/utils/mockAxiosKanban.js
src/views/kanban/Board.jsx
src/views/kanban/Column.jsx
src/views/kanban/Item.jsx
```

Create the folder tree if it doesn’t exist.

---

## 3.  Wire the mock at **app startup**

Add this import **once** in `src/index.jsx` (just after other global imports):

```jsx
// ⬇️ development‑only mock for Kanban endpoints
if (import.meta.env.DEV) {
  import('utils/mockAxiosKanban');
}
```

---

## 4.  Persist the Redux store

### 4.1 `src/store/index.js`

Replace the existing file with the diff below (or merge manually):

```diff
-import { configureStore } from '@reduxjs/toolkit';
-import reducer from './reducer';
+import { configureStore } from '@reduxjs/toolkit';
+import reducer from './reducer';
+import { persistStore, persistReducer, FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from 'redux-persist';
+import storage from 'redux-persist/lib/storage';

-const store = configureStore({
-  reducer,
-  middleware: (getDefaultMiddleware) =>
-    getDefaultMiddleware({
-      serializableCheck: false
-    })
-});
-
-export default store;
+const persistConfig = { key: 'root', storage, whitelist: ['kanban'] };
+const persistedReducer = persistReducer(persistConfig, reducer);
+
+export const store = configureStore({
+  reducer: persistedReducer,
+  middleware: (getDefaultMiddleware) =>
+    getDefaultMiddleware({
+      serializableCheck: {
+        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER]
+      }
+    })
+});
+
+export const persistor = persistStore(store);
```

### 4.2 `src/index.jsx`

Wrap your `<App />` with `PersistGate`:

```diff
-import store from './store';
+import { store, persistor } from './store';
+import { PersistGate } from 'redux-persist/integration/react';

-<Provider store={store}>
-  <App />
-</Provider>
+<Provider store={store}>
+  <PersistGate loading={null} persistor={persistor}>
+    <App />
+  </PersistGate>
+</Provider>
```

---

## 5.  Register the Kanban slice

`src/store/reducer.js`

```diff
+import kanbanReducer from './slices/kanban';

 export default combineReducers({
   // …other slices
+  kanban: kanbanReducer
 });
```

---

## 6.  Add the board route & sidebar link

### 6.1 `src/routes/MainRoutes.jsx`

```jsx
const KanbanBoard = Loadable(lazy(() => import('views/kanban/Board')));

{
  path: '/kanban',
  element: <KanbanBoard />
}
```

### 6.2 `src/menu-items/pages.js`

```js
{
  id: 'kanban-board',
  title: 'Kanban Board',
  type: 'item',
  url: '/kanban',
  icon: icons.Apps
}
```

---

## 7.  Place Bubba’s avatar

Put the PNG file here:

```
frontend/static/images/bubba_icon.png
```

The board looks for `/static/images/bubba_icon.png`.

---

## 8.  Run it 🏃‍♂️

```bash
npm run dev
```

Drag columns & cards, filter by story chips, reload the page – state persists locally ✨.

---

### Optional enhancements

* Add more POST mocks in `mockAxiosKanban.js` to cover **add/edit** flows.  
* Swap the mock for real FastAPI routes by deleting the import in **step 3**.

Happy building!
