import axios from "axios";
import { UserProfile } from "../../interfaces/models/userprofile";

const TEST_USER_ID = "687dfe868ba207c8b600db4e";

export const getProfile = async (): Promise<UserProfile> => {
  const res = await axios.get(
    "http://127.0.0.1:8000//test/get-user/${TEST_USER_ID}",
  ); // To be replaced with the backend endpoint
  const { _id, full_name, email, username } = res.data;
  // return res.data;
  return {
    id: _id,
    fullName: full_name,
    email,
    username,
  };
};

export const updateProfile = async (
  data: UserProfile,
): Promise<UserProfile> => {
  const res = await axios.put(
    "http://127.0.0.1:8000/test/update-user/{user_id}",
    data,
  ); // To be replaced with the backend endpoint
  return res.data;
};
