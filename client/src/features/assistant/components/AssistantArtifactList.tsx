import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { AssistantArtifact } from "@features/assistant/types";
import { api } from "@shared/api/http";

interface AssistantArtifactListProps {
  artifacts?: AssistantArtifact[];
}

type DownloadState = {
  status: "downloading" | "started" | "failed";
  attempts: number;
};

const AssistantArtifactList = ({ artifacts }: AssistantArtifactListProps) => {
  const [expandedArtifacts, setExpandedArtifacts] = useState<Record<string, boolean>>({});
  const [downloadingArtifact, setDownloadingArtifact] = useState<string | null>(null);
  const [downloadStates, setDownloadStates] = useState<Record<string, DownloadState>>({});
  const autoDownloadAttemptsRef = useRef<Record<string, boolean>>({});

  const getVisibleItems = (artifactKey: string, items: any[]) => {
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
    return (
      <div className="mt-2 flex flex-wrap gap-2">
        {actions.map((action: any, actionIndex) => {
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

  const downloadFileAction = async (artifactKey: string, data: Record<string, any>) => {
    const href = typeof data.href === "string" ? data.href : null;
    const metadata = (data.metadata || {}) as Record<string, any>;
    const quizId = typeof metadata.quiz_id === "string" ? metadata.quiz_id : null;
    const format = typeof metadata.format === "string" ? metadata.format : "pdf";
    const currentState = downloadStates[artifactKey];
    const attempts = currentState?.attempts || 0;
    const maxRetries = typeof data.max_retries === "number" ? data.max_retries : 3;
    if (!href || !quizId) {
      toast.error("Download details are incomplete.");
      return;
    }
    if (attempts >= maxRetries) {
      toast.error("Download retry limit reached. Please use the in-app Download Quiz button.");
      return;
    }

    setDownloadingArtifact(artifactKey);
    setDownloadStates((current) => ({
      ...current,
      [artifactKey]: {
        status: "downloading",
        attempts: (current[artifactKey]?.attempts || 0) + 1,
      },
    }));
    try {
      const response = await api.get(href, {
        responseType: "blob",
        params: {
          quiz_id: quizId,
          format,
        },
      });
      const contentDisposition = response.headers["content-disposition"];
      const matchedFilename = contentDisposition?.match(/filename=([^;]+)/i)?.[1];
      const fallbackName = typeof metadata.filename === "string" ? metadata.filename : `quiz.${format}`;
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
      setDownloadStates((current) => ({
        ...current,
        [artifactKey]: {
          status: "started",
          attempts: current[artifactKey]?.attempts || 1,
        },
      }));
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || "Failed to download quiz.");
      setDownloadStates((current) => ({
        ...current,
        [artifactKey]: {
          status: "failed",
          attempts: current[artifactKey]?.attempts || 1,
        },
      }));
    } finally {
      setDownloadingArtifact(null);
    }
  };

  useEffect(() => {
    if (!artifacts?.length) return;
    artifacts.forEach((artifact, index) => {
      if (artifact.type !== "file_action") return;
      const actionId = typeof artifact.data.action_id === "string" ? artifact.data.action_id : null;
      const artifactKey = actionId || `${artifact.type}-${index}`;
      if (!artifact.data.auto_execute) return;
      if (downloadStates[artifactKey]?.status === "started") return;
      if (autoDownloadAttemptsRef.current[artifactKey]) return;
      autoDownloadAttemptsRef.current[artifactKey] = true;
      void downloadFileAction(artifactKey, artifact.data);
    });
  }, [artifacts, downloadStates]);

  if (!artifacts?.length) return null;

  const renderResourceList = (artifact: AssistantArtifact, artifactKey: string) => {
    const items = Array.isArray(artifact.data.items) ? artifact.data.items : [];
    return (
      <div key={artifactKey} className="space-y-2">
        {typeof artifact.data.title === "string" && (
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            {artifact.data.title}
          </p>
        )}
        {getVisibleItems(artifactKey, items).map((item: any, itemIndex) => {
          const label = String(item.label || item.title || item.name || "Open");
          const href = typeof item.href === "string" ? item.href : null;
          const key = String(item.id || item.href || `${artifactKey}-${itemIndex}`);
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
        })}
        {renderListToggle(artifactKey, items.length)}
      </div>
    );
  };

  return (
    <div className="mt-3 space-y-2">
      {artifacts.map((artifact, index) => {
        const actionId = typeof artifact.data.action_id === "string" ? artifact.data.action_id : null;
        const artifactKey = actionId || `${artifact.type}-${index}`;

        if (artifact.type === "resource_list") {
          return renderResourceList(artifact, artifactKey);
        }

        if (artifact.type === "resource") {
          const label = String(artifact.data.label || "Open");
          const href = typeof artifact.data.href === "string" ? artifact.data.href : null;
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
          const downloadState = downloadStates[artifactKey];
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
          const maxRetries = typeof artifact.data.max_retries === "number" ? artifact.data.max_retries : 3;
          const attempts = downloadState?.attempts || 0;
          const hasReachedRetryLimit = attempts >= maxRetries;
          if (hasReachedRetryLimit && downloadState?.status === "failed") {
            return (
              <div
                key={artifactKey}
                className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900"
              >
                Download could not start from the assistant. Please use the in-app Download Quiz button.
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
              {String(artifact.data.label || artifact.data.message || "Completed")}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

export default AssistantArtifactList;
