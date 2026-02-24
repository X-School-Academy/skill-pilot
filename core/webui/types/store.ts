import { Assignment } from "./assignment";
import { UserModel } from "./user";

export interface ReduxStoreState {
  user: {
    user: UserModel;
  };
  assignment: {
    assignment: Assignment;
  };
  apiServerToken: {
    apiServerToken: string | undefined;
  };
}