import { useState } from "react";
import ProfileView from "../../components/profile/profileView";
import ProfileEditForm from "../../components/profile/profileEditForm";
import { UserProfile } from "../../interfaces/models/userprofile";

const mockUser: UserProfile = {
  fullName: "Jean Test",
  email: "benuus1@gmail.com",
  username: "JEAN",
};

export default function ProfilePage() {
  const [user, setUser] = useState<UserProfile>(mockUser);
  const [editMode, setEditMode] = useState(false);

  const handleUpdate = (updatedUser: UserProfile) => {
    setUser(updatedUser);
    setEditMode(false);
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-4 shadow rounded bg-white">
      <h1 className="text-2xl font-bold mb-4 text-[#111827]">My Profile</h1>
      {editMode ? (
        <ProfileEditForm
          user={user}
          onCancel={() => setEditMode(false)}
          onSave={handleUpdate}
        />
      ) : (
        <ProfileView user={user} onEdit={() => setEditMode(true)} />
      )}
    </div>
  );
}

// TO BE USED IN THE FUTURE FOR WHEN API IS READY
// import { useEffect, useState } from "react";
// import ProfileView from "../../components/profile/profileView";
// import ProfileEditForm from "../../components/profile/profileEditForm";
// import { getProfile, updateProfile } from "../../lib/functions/profile";
// import { UserProfile } from "../../interfaces/models/userprofile";

// export default function ProfilePage() {
//   const [user, setUser] = useState<UserProfile | null>(null);
//   const [editMode, setEditMode] = useState(false);

//   useEffect(() => {
//     getProfile()
//       .then((data) => setUser(data))
//       .catch((err) => console.error("Error fetching profile", err));
//   }, []);

//   const handleUpdate = async (updatedUser: UserProfile) => {
//     try {
//       const data = await updateProfile(updatedUser);
//       setUser(data);
//       setEditMode(false);
//     } catch (err) {
//       console.error("Error updating profile", err);
//     }
//   };

//   if (!user) return <div className="p-4">Loading...</div>;

//   return (
//     <div className="max-w-md mx-auto mt-10 p-4 shadow rounded bg-white">
//       <h1 className="text-2xl font-bold mb-4">My Profile</h1>
//       {editMode ? (
//         <ProfileEditForm user={user} onCancel={() => setEditMode(false)} onSave={handleUpdate} />
//       ) : (
//         <ProfileView user={user} onEdit={() => setEditMode(true)} />
//       )}
//     </div>
//   );
// }
