import { UserModel } from "../types/user";
import {
  getHeader,
  getStrapiAuthHeader,
} from "./auth-header";
import { decodeBase64, encodeBase64 } from "./utils";

const QUERY_USER = `
query ($id: ID!) {
  usersPermissionsUser(id: $id) {
    data{
      id
      attributes{
        username
        email
        membership
        avatar {
          data{
            attributes{
              url
            }
          }
        }
        subscription_date
        subscription
        github_token
        online_course{
          id
          role
          auth
          course_data
          level{
            data{
              id
              attributes{
                name
                description
              }
            }
          }
          session{
            data{
              id
              attributes{
                session_id
                course_name
                max_limit_student
                max_limit_teacher
                expired_time
                holder{
                  data{
                    attributes{
                      username
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
`;

export const getBrowserCachedUser = () => {
  const cachedUser = localStorage.getItem("user");
  if (cachedUser == null) {
    return;
  }
  const userString = decodeBase64(cachedUser);
  const userModel: UserModel = JSON.parse(userString);
  return userModel;
};

export const updateBrowserCachedUser = (user: UserModel) =>{
  const userData = encodeBase64(JSON.stringify(user))
  //use info
  localStorage.setItem("user", userData);
}

export const findUser = async (
  userId: number | undefined,
  jwt: string | undefined
) => {
  if (!userId || !jwt) return;
  try {
    const queryRes = await fetch(
      process.env.NEXT_INTERNAL_API_URL + "/graphql",
      {
        method: "POST",
        headers: getHeader(userId.toString(), jwt),
        body: JSON.stringify({
          query: QUERY_USER,
          variables: {
            id: userId,
          },
        }),
      }
    );
    const res = await queryRes.json();
    const userMode: UserModel | undefined = res.data.usersPermissionsUser.data;
    return userMode;
  } catch (error) {
    console.log('fetch user failed: ',error);
  }
};

