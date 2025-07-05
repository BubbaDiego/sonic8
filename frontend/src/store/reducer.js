// third party
import { combineReducers } from 'redux';

// project imports
import snackbarReducer from './slices/snackbar';
import alertThresholdsReducer from './slices/alertThresholds';

// ==============================|| COMBINE REDUCER ||============================== //

const reducer = combineReducers({
  snackbar: snackbarReducer,
  alertThresholds: alertThresholdsReducer
});

export default reducer;
