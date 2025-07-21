// third party
import { combineReducers } from 'redux';

// project imports
import snackbarReducer from './slices/snackbar';
import alertThresholdsReducer from './slices/alertThresholds';
import kanbanReducer from './slices/kanban';

// ==============================|| COMBINE REDUCER ||============================== //

const reducer = combineReducers({
  snackbar: snackbarReducer,
  thresholds: alertThresholdsReducer,
  kanban: kanbanReducer

});

export default reducer;
