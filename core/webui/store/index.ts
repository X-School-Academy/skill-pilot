import { configureStore, ThunkAction, Action } from "@reduxjs/toolkit";

import assignmentReducer from "../features/assignment/assignmentSlice";
import userReducer from "../features/user/userSlice";
import apiServerReducer from "../features/apiServerToken/apiServerSlice";
import { ReduxStoreState } from "../types/store";

export function makeStore() {
  return configureStore({
    reducer: {
      assignment: assignmentReducer,
      user: userReducer,
      apiServerToken: apiServerReducer,
    },
  });
}

const store = makeStore();

export type AppState = ReturnType<typeof store.getState>;

export type AppDispatch = typeof store.dispatch;

export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  AppState,
  unknown,
  Action<string>
>;

export default store;
