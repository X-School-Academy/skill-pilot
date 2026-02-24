import {
  AnyAction,
  createAsyncThunk,
  createSlice,
  Dispatch,
  PayloadAction,
} from "@reduxjs/toolkit";

import type { AppState, AppThunk } from "../../store";
import { AssignmentStateWithUser } from "../../types/assignment";
import { findUser, getBrowserCachedUser } from "../../libs/user";
import logger from "../../libs/logger";

const initialState: AssignmentStateWithUser = {
  value: 0,
  status: "idle",
  user: {
    id: "0",
    attributes: {
      username: "",
      email: "",
      avatar: {
        data: {
          attributes: {
            url: "",
          },
        },
      },
      github_token: null,
    },
  },
};

export const userSlice = createSlice({
  name: "user",
  initialState,
  // The `reducers` field lets us define reducers and generate associated actions
  reducers: {
    store: (state, action) => {
      state.user = action.payload;
    },
  },
  extraReducers: (builder) => {},
});

export const { store } = userSlice.actions;

export const selectUser = (state: AppState) => state.user.user;

export const fetchUser = async (session: any) => {
  return async (dispatch: any) => {
    try {
      const cachedUser = getBrowserCachedUser();
      if (cachedUser != null) {
        return dispatch(store(cachedUser));
      }
      const res = await findUser(session.id, session.jwt);
      return dispatch(store(res));
    } catch (error) {
      logger.error(error);
      return dispatch({
        payload: undefined,
        type: "user/store",
      });
    }
  };
};

export default userSlice.reducer;
