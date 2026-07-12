import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  AssistantArtifact,
  AssistantArtifactAction,
  AssistantFileActionArtifact,
  AssistantResourceItem,
} from "@features/assistant/types";
import { api } from "@shared/api/http";

interface AssistantArtifactListProps {
  artifacts?: AssistantArtifact[];
}

type DownloadState = {
  status: "downloading" | "started" | "failed";
  attempts: number;
};

type ApiErrorLike = {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
};

const DOWNLOAD_STATE_STORAGE_PREFIX = "quizapp.assistant.download.";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === "object" && !Array.isArray(value);

const getString = (value: unknown): string | null =>
  typeof value === "string" && value.trim() ? value : null;

const getNumber = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const isAssistantArtifactAction = (
  value: unknown,
): value is AssistantArtifactAction =>
  isRecord(value) && value.type === "copy_to_clipboard";

const readPersistedDownloadState = (
  artifactKey: string,
): DownloadState | null => {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(
    `${DOWNLOAD_STATE_STORAGE_PREFIX}${artifactKey}`,
  );
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return null;
    const status = parsed.status;
    const attempts = parsed.attempts;
    if (
      (status === "downloading" ||
        status === "started" ||
        status === "failed") &&
      typeof attempts === "number"
    ) {
      return {
        status: status === "downloading" ? "failed" : status,
        attempts,
      };
    }
  } catch {
    return null;
  }
  return null;
};

const persistDownloadState = (artifactKey: string, state: DownloadState) => {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(
    `${DOWNLOAD_STATE_STORAGE_PREFIX}${artifactKey}`,
    JSON.stringify(state),
  );
};

const AssistantArtifactList = ({ artifacts }: AssistantArtifactListProps) => {
  const [expandedArtifacts, setExpandedArtifacts] = useState<
    Record<string, boolean>
  >({});
  const [downloadingArtifact, setDownloadingArtifact] = useState<string | null>(
    null,
  );
  const [downloadStates, setDownloadStates] = useState<
    Record<string, DownloadState>
  >({});
  const autoDownloadAttemptsRef = useRef<Record<string, boolean>>({});

  const getDownloadState = (artifactKey: string): DownloadState | undefined =>
    downloadStates[artifactKey] ||
    readPersistedDownloadState(artifactKey) ||
    undefined;

  const setDownloadState = (artifactKey: string, state: DownloadState) => {
    persistDownloadState(artifactKey, state);
    setDownloadStates((current) => ({
      ...current,
      [artifactKey]: state,
    }));
  };

  const getVisibleItems = (
    artifactKey: string,
    items: AssistantResourceItem[],
  ) => {
    if (expandedArtifacts[artifactKey]) return items;
    return items.slice(0, 8);
  };

  const renderListToggle = (artifactKey: string, total: number) => {
    if (total <= 8) return null;
    const isExpanded = Boolean(expandedArtifacts[artifactKey]);
    return (
      <button
        type="button"
        onClick={() =>
          setExpandedArtifacts((current) => ({
            ...current,
            [artifactKey]: !isExpanded,
          }))
        }
        className="text-xs font-semibold text-blue-700 transition hover:text-blue-900"
      >
        {isExpanded ? "Show less" : `Show all ${total}`}
      </button>
    );
  };

  const copyToClipboard = async (value: unknown) => {
    const text = typeof value === "string" ? value : "";
    if (!text) {
      toast.error("There is nothing to copy.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied to clipboard.");
    } catch {
      toast.error("Could not copy to clipboard.");
    }
  };

  const renderArtifactActions = (actions: unknown) => {
    if (!Array.isArray(actions) || actions.length === 0) return null;
    const typedActions = actions.filter(isAssistantArtifactAction);
    return (
      <div className="mt-2 flex flex-wrap gap-2">
        {typedActions.map((action, actionIndex) => {
          if (action?.type !== "copy_to_clipboard") return null;
          return (
            <button
              key={`${String(action.label || "copy")}-${actionIndex}`}
              type="button"
              onClick={() => copyToClipboard(action.value)}
              className="rounded-lg border border-blue-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-blue-800 transition hover:border-blue-300 hover:bg-blue-50"
            >
              {String(action.label || "Copy")}
            </button>
          );
        })}
      </div>
    );
  };

  const downloadFileAction = async (
    artifactKey: string,
    data: AssistantFileActionArtifact["data"],
  ) => {
    const href = getString(data.href);
    const metadata = isRecord(data.metadata) ? data.metadata : {};
    const quizId = getString(metadata.quiz_id);
    const format = getString(metadata.format) || "pdf";
    const currentState = getDownloadState(artifactKey);
    const attempts = currentState?.attempts || 0;
    const maxRetries = getNumber(data.max_retries) || 3;
    if (!href || !quizId) {
      toast.error("Download details are incomplete.");
      return;
    }
    if (attempts >= maxRetries) {
      toast.error(
        "Download retry limit reached. Please use the in-app Download Quiz button.",
      );
      return;
    }

    setDownloadingArtifact(artifactKey);
    setDownloadState(artifactKey, {
      status: "downloading",
      attempts: attempts + 1,
    });
    try {
      const response = await api.get(href, {
        responseType: "blob",
        params: {
          quiz_id: quizId,
          format,
        },
      });
      const contentDisposition = response.headers["content-disposition"];
      const matchedFilename =
        contentDisposition?.match(/filename=([^;]+)/i)?.[1];
      const fallbackName = getString(metadata.filename) || `quiz.${format}`;
      const resolvedName = matchedFilename?.replace(/"/g, "") || fallbackName;
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", resolvedName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Quiz download started.");
      setDownloadState(artifactKey, {
        status: "started",
        attempts: attempts + 1,
      });
    } catch (error: unknown) {
      const typedError = error as ApiErrorLike;
      toast.error(
        typedError?.response?.data?.detail ||
          typedError?.message ||
          "Failed to download quiz.",
      );
      setDownloadState(artifactKey, {
        status: "failed",
        attempts: attempts + 1,
      });
    } finally {
      setDownloadingArtifact(null);
    }
  };

  useEffect(() => {
    if (!artifacts?.length) return;
    artifacts.forEach((artifact, index) => {
      if (artifact.type !== "file_action") return;
      const actionId = getString(artifact.data.action_id);
      const artifactKey = actionId || `${artifact.type}-${index}`;
      if (!artifact.data.auto_execute) return;
      if (getDownloadState(artifactKey)) return;
      if (autoDownloadAttemptsRef.current[artifactKey]) return;
      autoDownloadAttemptsRef.current[artifactKey] = true;
      void downloadFileAction(artifactKey, artifact.data);
    });
  }, [artifacts, downloadStates]);

  if (!artifacts?.length) return null;

  const renderResourceList = (
    artifact: AssistantArtifact,
    artifactKey: string,
  ) => {
    const items = Array.isArray(artifact.data.items)
      ? (artifact.data.items.filter(isRecord) as AssistantResourceItem[])
      : [];
    return (
      <div key={artifactKey} className="space-y-2">
        {typeof artifact.data.title === "string" && (
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            {artifact.data.title}
          </p>
        )}
        {getVisibleItems(artifactKey, items).map(
          (item: AssistantResourceItem, itemIndex) => {
            const label = String(
              item.label || item.title || item.name || "Open",
            );
            const href = typeof item.href === "string" ? item.href : null;
            const key = String(
              item.id || item.href || `${artifactKey}-${itemIndex}`,
            );
            if (href) {
              return (
                <Link
                  key={key}
                  href={href}
                  className="block rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-900 transition hover:border-blue-300 hover:bg-blue-100"
                >
                  {label}
                </Link>
              );
            }
            return (
              <div
                key={key}
                className="rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-900"
              >
                {label}
              </div>
            );
          },
        )}
        {renderListToggle(artifactKey, items.length)}
      </div>
    );
  };

  return (
    <div className="mt-3 space-y-2">
      {artifacts.map((artifact, index) => {
        const actionId = getString(artifact.data.action_id);
        const artifactKey = actionId || `${artifact.type}-${index}`;

        if (artifact.type === "resource_list") {
          return renderResourceList(artifact, artifactKey);
        }

        if (artifact.type === "resource") {
          const label = String(artifact.data.label || "Open");
          const href =
            typeof artifact.data.href === "string" ? artifact.data.href : null;
          if (!href) {
            return (
              <div
                key={artifactKey}
                className="rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900"
              >
                {label}
                {renderArtifactActions(artifact.data.actions)}
              </div>
            );
          }
          return (
            <div key={artifactKey}>
              <Link
                href={href}
                className="block rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-900 transition hover:border-blue-300 hover:bg-blue-100"
              >
                {label}
              </Link>
              {renderArtifactActions(artifact.data.actions)}
            </div>
          );
        }

        if (artifact.type === "file_action") {
          const downloadState = getDownloadState(artifactKey);
          if (downloadState?.status === "started") {
            return (
              <div
                key={artifactKey}
                className="rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900"
              >
                Download started.
              </div>
            );
          }

          const label = String(artifact.data.label || "Download");
          const isDownloading = downloadingArtifact === artifactKey;
          const maxRetries = getNumber(artifact.data.max_retries) || 3;
          const attempts = downloadState?.attempts || 0;
          const hasReachedRetryLimit = attempts >= maxRetries;
          if (hasReachedRetryLimit && downloadState?.status === "failed") {
            return (
              <div
                key={artifactKey}
                className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900"
              >
                Download could not start from the assistant. Please use the
                in-app Download Quiz button.
              </div>
            );
          }

          return (
            <button
              key={artifactKey}
              type="button"
              onClick={() => downloadFileAction(artifactKey, artifact.data)}
              disabled={isDownloading}
              className="block w-full rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-blue-900 transition hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isDownloading
                ? "Preparing download..."
                : downloadState?.status === "failed"
                  ? `Retry download (${attempts}/${maxRetries})`
                  : label}
            </button>
          );
        }

        if (artifact.type === "status") {
          return (
            <div
              key={artifactKey}
              className="rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900"
            >
              {String(
                artifact.data.label || artifact.data.message || "Completed",
              )}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

export default AssistantArtifactList;
