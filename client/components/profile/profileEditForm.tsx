import { useState } from "react";
import { UserProfile } from "../../interfaces/models/userprofile";

interface ProfileEditFormProps {
  user: UserProfile;
  onCancel: () => void;
  onSave: (updatedUser: UserProfile) => void;
}

export default function ProfileEditForm({
  user,
  onCancel,
  onSave,
}: ProfileEditFormProps) {
  const [formData, setFormData] = useState<UserProfile>(user);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-[#111827]">
      <div>
        <label className="block text-sm font-medium text-[#111827]">
          Full Name
        </label>
        <input
          name="fullName"
          value={formData.fullName}
          onChange={handleChange}
          className="w-full p-2 border border-[#d1d5db] rounded bg-white"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-[#111827]">
          Email
        </label>
        <input
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          className="w-full p-2 border border-[#d1d5db] rounded bg-white"
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Username</label>
        <input
          name="username"
          value={formData.username}
          onChange={handleChange}
          className="w-full p-2 border rounded text-[#111827]"
        />
      </div>

      <div className="flex justify-between mt-4">
        <button
          type="submit"
          className="bg-[#0F2C59] hover:bg-[#0a1e3f] text-white px-4 py-2 rounded"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="bbg-[#F3F4F6] text-[#111827] px-4 py-2 rounded"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
