// third party
import { configureStore } from '@reduxjs/toolkit';
import { useDispatch as useAppDispatch, useSelector as useAppSelector } from 'react-redux';

import {
  persistStore,
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER
} from 'redux-persist';
import storage from 'redux-persist/lib/storage';

// project imports
import rootReducer from './reducer';

// ==============================|| REDUX - MAIN STORE ||============================== //

const persistConfig = { key: 'root', storage, whitelist: ['kanban'] };
const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER]
      }
    })
});

export const persistor = persistStore(store);

const { dispatch } = store;

function useDispatch() {
  return useAppDispatch();
}

const useSelector = useAppSelector;

export { store, dispatch, useSelector, useDispatch };
