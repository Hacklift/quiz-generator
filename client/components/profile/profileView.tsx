import { UserProfile } from "../../interfaces/models/userprofile";

interface ProfileViewProps {
  user: UserProfile;
  onEdit: () => void;
}

export default function ProfileView({ user, onEdit }: ProfileViewProps) {
  return (
    <div className="space-y-4 text-[#111827]">
      <p>
        <strong>Full Name:</strong> {user.fullName}
      </p>
      <p>
        <strong>Email:</strong> {user.email}
      </p>
      <p>
        <strong>Username:</strong> {user.username}
      </p>
      <button
        onClick={onEdit}
        className="mt-4 bg-[#0F2C59] hover:bg-[#0a1e3f] text-white px-4 py-2 rounded"
      >
        Edit Profile
      </button>
    </div>
  );
}
