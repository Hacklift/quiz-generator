import { ChangeEvent, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { useOrganization } from "@features/organizations/context/organizationContext";

type Props = { className?: string };

export default function OrganizationSwitcher({ className = "" }: Props) {
  const { memberships, activeOrganization, isLoading, switchOrganization } = useOrganization();
  const [isSwitching, setIsSwitching] = useState(false);

  if (isLoading || !activeOrganization) {
    return null;
  }

  const onChange = async (event: ChangeEvent<HTMLSelectElement>) => {
    setIsSwitching(true);
    try {
      await switchOrganization(event.target.value);
      toast.success("Organization switched.");
    } catch {
      toast.error("Unable to switch organization.");
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {memberships.length > 1 ? (
        <label className="text-[12px] font-bold text-ink/70">
          <span className="sr-only">Active organization</span>
          <select
            value={activeOrganization.organization_id}
            onChange={(event) => void onChange(event)}
            disabled={isSwitching}
            className="max-w-[176px] border-2 border-divider bg-paper px-2 py-1 text-[13px] font-bold text-ink disabled:opacity-60"
          >
            {memberships.map((membership) => (
              <option key={membership.organization_id} value={membership.organization_id}>
                {membership.organization_name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {activeOrganization.role === "owner" || activeOrganization.role === "admin" ? (
        <Link href="/organizations/manage" className="text-[12px] font-extrabold text-brand hover:underline">
          Organizations
        </Link>
      ) : null}
    </div>
  );
}
