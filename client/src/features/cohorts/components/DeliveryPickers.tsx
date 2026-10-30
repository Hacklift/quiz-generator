import { useEffect, useRef, useState } from "react";
import { BTN_GHOST } from "@shared/ui/quizwerk";
import { cohortDeliveryApi, type MemberOption, type Page } from "../api/cohortDeliveryApi";
import { errorMessage, FIELD, useScopeGuard } from "./DeliveryShell";

export function useDeliveryPages<T>(load: (cursor?: string) => Promise<Page<T>>, initialPage?: Page<T>) {
  const [items, setItems] = useState<T[]>(initialPage?.items ?? []);
  const [cursor, setCursor] = useState<string | null>(initialPage?.next_cursor ?? null);
  const [loading, setLoading] = useState(!initialPage);
  const [error, setError] = useState<string | null>(null);
  const loader = useRef(load);
  loader.current = load;
  const generation = useRef(0);
  const busy = useRef(false);
  const guard = useScopeGuard();
  const fetchPage = async (next?: string) => {
    if (busy.current) return;
    busy.current = true;
    const version = generation.current;
    const isCurrent = guard;
    setLoading(true);
    setError(null);
    try {
      const page = await loader.current(next);
      if (!isCurrent() || version !== generation.current) return;
      setItems((previous) => next ? [...previous, ...page.items] : page.items);
      setCursor(page.next_cursor);
    } catch (failure) {
      if (isCurrent() && version === generation.current) {
        const status = (failure as { response?: { status?: number } })?.response?.status;
        if (status === 403 || status === 404) { setItems([]); setCursor(null); }
        setError(errorMessage(failure, "Unable to load records. Please try again."));
      }
    } finally {
      if (version === generation.current) {
        busy.current = false;
        if (isCurrent()) setLoading(false);
      }
    }
  };
  useEffect(() => {
    if (!initialPage) void fetchPage();
    return () => { generation.current += 1; busy.current = false; };
    // The enclosing scope boundary remounts the list when identity or tenant changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { items, cursor, loading, error, more: () => fetchPage(cursor ?? undefined), refresh: () => {
    generation.current += 1;
    busy.current = false;
    return fetchPage();
  } };
}

export function MoreRecords({ cursor, loading, error, more }: {
  cursor: string | null; loading: boolean; error: string | null; more: () => void;
}) {
  return <>{loading && <p role="status">Loading records...</p>}{error && <p role="alert">{error}</p>}
    {(cursor || error) && <button type="button" disabled={loading} onClick={more} className={`${BTN_GHOST} mt-3 disabled:opacity-50`}>{error ? "Retry loading" : "Load more"}</button>}</>;
}

export function MemberPicker({ selected, onChange, multiple = true, load = cohortDeliveryApi.memberOptions }: {
  selected: string[]; onChange: (ids: string[]) => void; multiple?: boolean;
  load?: (cursor?: string) => Promise<Page<MemberOption>>;
}) {
  const page = useDeliveryPages<MemberOption>(load);
  return <fieldset className="my-4 border-2 border-divider p-4">
    <legend className="px-2 font-bold">Active organization members</legend>
    <p className="mb-3 text-sm text-ink/70">Only active members of this workspace can be selected.</p>
    <div className="max-h-64 space-y-2 overflow-y-auto">
      {page.items.map((member) => <label key={member.user_id} className="flex items-center gap-3 p-2 hover:bg-ink/5">
        <input type={multiple ? "checkbox" : "radio"} name="organization-recipient" checked={selected.includes(member.user_id)}
          onChange={(event) => onChange(multiple ? event.target.checked ? [...selected, member.user_id] : selected.filter((value) => value !== member.user_id) : [member.user_id])} />
        <span>{member.name || member.user_id}</span>
      </label>)}
    </div>
    {!page.loading && !page.items.length && !page.error && <p>No eligible members found.</p>}
    <MoreRecords {...page} />
    {multiple && <p className="mt-3 text-sm">{selected.length} selected</p>}
  </fieldset>;
}

export function PagedSelect<T>({ label, load, value, onChange, identify, describe, filter }: {
  label: string; load: (cursor?: string) => Promise<Page<T>>; value: string;
  onChange: (value: string) => void; identify: (item: T) => string; describe: (item: T) => string;
  filter?: (item: T) => boolean;
}) {
  const page = useDeliveryPages(load);
  return <div><label className="block font-bold">{label}
    <select className={FIELD} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Select {label.toLowerCase()}</option>
      {value && !page.items.some((item) => identify(item) === value) && <option value={value}>Current selection (load more to view)</option>}
      {page.items.filter((item) => !filter || filter(item)).map((item) => <option key={identify(item)} value={identify(item)}>{describe(item)}</option>)}
    </select></label><MoreRecords {...page} /></div>;
}
