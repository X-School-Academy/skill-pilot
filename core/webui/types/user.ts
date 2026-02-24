export interface UserModel {
  id: string;
  attributes: User;
}

export interface User {
  username: string;
  email: string;
  avatar?: {
    data?: {
      attributes?: {
        url?: string;
      };
    };
  };
  membership?: string;
  subscription_date?: Date;
  subscription?: string;
  github_token: string | null;
}

export type Role = 'student' | 'teacher';

export interface RoleUser{
  role: 'student' | 'teacher';
  user: UserModel
}
