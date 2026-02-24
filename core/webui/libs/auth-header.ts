export const getApiServerAuthHeader = (
  userId: string,
  apiServerToken: string | undefined
) => {
  return {
    Authorization: `Bearer ${apiServerToken}`,
    "user-id": userId,
  };
};

export const getStrapiAuthHeader = (jwt: string | undefined) => {
  return {
    Authorization: `Bearer ${jwt}`,
    "Content-Type": "application/json",
  };
};

export const getJsonAuthHeader = (header: HeadersInit | any) => {
  return {
    ...header,
    "Content-Type": "application/json",
  };
};

export const getHeader = (userId: string, token: string | undefined) => {
  return {
    Authorization: `Bearer ${token}`,
    "user-id": userId,
    "Content-Type": "application/json",
  };
};
