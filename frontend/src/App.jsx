import { useEffect, useMemo, useState } from "react";
import ChatPanel from "./components/ChatPanel.jsx";
import EditorPanel from "./components/EditorPanel.jsx";
import {
  createChatSession,
  getChatSession,
  reviewTerraformDiff,
  sendChatMessage,
} from "./services/api.js";

const SERVICE_OPTIONS = [
  "Networking",
  "Compute",
  "Load Balancer",
  "Database",
  "Object Storage",
  "Functions",
  "API Gateway",
  "Security",
];

const STARTER_TERRAFORM = `terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}
`;

const SMALL_TALK_TOKENS = new Set([
  "hi",
  "hello",
  "hey",
  "yo",
  "hola",
  "thanks",
  "thank you",
]);

function normalizeTerraform(text) {
  const trimmed = (text || "")
    .split("\n")
    .map((line) => line.replace(/\s+$/g, ""))
    .join("\n")
    .trimEnd();
  return trimmed ? `${trimmed}\n` : "";
}

function normalizeMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }
  return messages.map((msg, idx) => ({
    id: msg.id || `${msg.role || "unknown"}-${idx}`,
    role: msg.role || "assistant",
    content: msg.content || "",
    created_at: msg.created_at || "",
    intent: msg.intent || null,
  }));
}

function looksLikeSmallTalk(text) {
  const lowered = (text || "").trim().toLowerCase();
  if (!lowered) {
    return false;
  }
  const normalized = lowered.replace(/\s+/g, " ");
  if (SMALL_TALK_TOKENS.has(normalized)) {
    return true;
  }
  if (normalized.endsWith("?")) {
    return true;
  }
  return false;
}

export default function App() {
  const [selectedServices, setSelectedServices] = useState(["Networking", "Compute"]);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState([]);
  const [draftMessage, setDraftMessage] = useState("");

  const [requirementsContext, setRequirementsContext] = useState("");
  const [generatedTerraform, setGeneratedTerraform] = useState("");
  const [reviewedTerraform, setReviewedTerraform] = useState("");
  const [editorTerraform, setEditorTerraform] = useState(STARTER_TERRAFORM);
  const [changeSummary, setChangeSummary] = useState("");
  const [cleanupScript, setCleanupScript] = useState("");
  const [diffLines, setDiffLines] = useState([]);
  const [clarification, setClarification] = useState(null);
  const [resolvedIntent, setResolvedIntent] = useState("");

  const [isInitializing, setIsInitializing] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [pendingIntent, setPendingIntent] = useState("");

  function applySessionState(session) {
    setSessionId(session.session_id || "");
    setMessages(normalizeMessages(session.messages));
    setRequirementsContext(session.requirements_context || "");
    const generated = normalizeTerraform(session.generated_terraform || "");
    const reviewed = normalizeTerraform(session.reviewed_terraform || "");
    setGeneratedTerraform(generated || STARTER_TERRAFORM);
    setReviewedTerraform(reviewed || generated || STARTER_TERRAFORM);
    setEditorTerraform(reviewed || generated || STARTER_TERRAFORM);
    setChangeSummary(session.change_summary || "");
    setCleanupScript(session.cleanup_script || "");
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrapSession() {
      setIsInitializing(true);
      setErrorMessage("");
      try {
        const created = await createChatSession(selectedServices);
        if (cancelled) return;
        applySessionState(created);
        const reloaded = await getChatSession(created.session_id);
        if (cancelled) return;
        applySessionState(reloaded);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error?.message || "Failed to initialize chat session.");
        }
      } finally {
        if (!cancelled) {
          setIsInitializing(false);
        }
      }
    }

    bootstrapSession();
    return () => {
      cancelled = true;
    };
    // Initialize once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function postMessage(message, intent = "auto") {
    if (!sessionId) {
      setErrorMessage("Session not initialized yet.");
      return;
    }

    setIsWorking(true);
    setPendingIntent(intent || "auto");
    setErrorMessage("");
    setClarification(null);
    try {
      const response = await sendChatMessage({
        sessionId,
        message,
        intent,
        services: selectedServices,
      });
      applySessionState(response);
      setResolvedIntent(response.resolved_intent || "");
      setClarification(response.clarification || null);
      setDiffLines([]);
    } catch (error) {
      setErrorMessage(error?.message || "Chat request failed.");
    } finally {
      setIsWorking(false);
      setPendingIntent("");
    }
  }

  async function handleSend(overrideMessage) {
    const text = (overrideMessage ?? draftMessage).trim();
    if (!text || isWorking) {
      return;
    }
    setDraftMessage("");
    const hasDraft = Boolean(generatedTerraform.trim() || reviewedTerraform.trim());
    let intent = "chat";
    if (!looksLikeSmallTalk(text)) {
      intent = hasDraft ? "refine" : "generate";
    }
    await postMessage(text, intent);
  }

  async function handleGenerateFromContext() {
    if (isWorking) {
      return;
    }
    await postMessage("", "generate");
  }

  async function handleRunReview() {
    if (isWorking) {
      return;
    }
    await postMessage("", "review");
  }

  async function handleRunCleanup() {
    if (isWorking) {
      return;
    }
    await postMessage("", "cleanup");
  }

  function toggleService(service) {
    setSelectedServices((prev) => {
      if (prev.includes(service)) {
        return prev.filter((item) => item !== service);
      }
      return [...prev, service];
    });
  }

  function handleFormatTerraform() {
    setEditorTerraform((prev) => normalizeTerraform(prev));
  }

  function handleResetTerraform() {
    setEditorTerraform(reviewedTerraform || generatedTerraform || STARTER_TERRAFORM);
  }

  async function handleReviewDiff() {
    if (!reviewedTerraform.trim()) {
      setErrorMessage("Generate or refine terraform first before running diff review.");
      return;
    }
    setIsReviewing(true);
    setErrorMessage("");
    try {
      const result = await reviewTerraformDiff(reviewedTerraform, editorTerraform);
      setDiffLines(Array.isArray(result.diff_lines) ? result.diff_lines : []);
    } catch (error) {
      setErrorMessage(error?.message || "Failed to compute diff.");
    } finally {
      setIsReviewing(false);
    }
  }

  const requirementsPreview = useMemo(
    () => requirementsContext || "No composed requirement yet.",
    [requirementsContext]
  );
  const showInfraLoading = isWorking && pendingIntent !== "chat";
  const hasTerraformDraft = Boolean(generatedTerraform.trim() || reviewedTerraform.trim());
  const hasReviewedDraft = Boolean(reviewedTerraform.trim());

  const loadingMeta = useMemo(() => {
    const lookup = {
      auto: {
        title: "Processing Request",
        subtitle: "Resolving intent and applying your latest instruction.",
        steps: ["Detect", "Apply", "Return"],
      },
      generate: {
        title: "Generating Terraform Draft",
        subtitle: "Creating infrastructure draft from your requirements.",
        steps: ["Parse", "Generate", "Return"],
      },
      refine: {
        title: "Applying Refinement",
        subtitle: "Updating your current Terraform draft with requested changes.",
        steps: ["Load Draft", "Refine", "Return"],
      },
      review: {
        title: "Running Security Review",
        subtitle: "Checking draft against compliance guidance and hardening it.",
        steps: ["Analyze", "Harden", "Summarize"],
      },
      cleanup: {
        title: "Generating Cleanup Script",
        subtitle: "Producing dependency-aware teardown instructions.",
        steps: ["Inspect", "Compose", "Return"],
      },
      chat: {
        title: "Asking OCI Assistant",
        subtitle: "Generating contextual response from session memory.",
        steps: ["Context", "Infer", "Respond"],
      },
    };
    return lookup[pendingIntent] || lookup.auto;
  }, [pendingIntent]);

  return (
    <div className="page-wrap">
      {showInfraLoading ? (
        <div className="infra-loading-screen" role="status" aria-live="polite">
          <div className="infra-loading-card">
            <p className="infra-loading-kicker">Proviso Engine</p>
            <h2>{loadingMeta.title}</h2>
            <p>{loadingMeta.subtitle}</p>
            <div className="infra-loading-track" aria-hidden="true">
              <span />
            </div>
            <div className="infra-loading-steps" aria-hidden="true">
              {loadingMeta.steps.map((step) => (
                <span key={step}>{step}</span>
              ))}
            </div>
          </div>
        </div>
      ) : null}
      <div className="page">
        <header className="header">
          <div>
            <p className="kicker">Proviso Frontend</p>
            <h1>Infrastructure Chat + Terraform Editor</h1>
          </div>
          <div className="header-actions">
            <button
              className="btn"
              type="button"
              onClick={handleGenerateFromContext}
              disabled={isWorking || isInitializing}
            >
              {isWorking ? "Working..." : "Generate Draft"}
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={handleRunReview}
              disabled={isWorking || isInitializing || !hasTerraformDraft}
            >
              Run Review
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={handleRunCleanup}
              disabled={isWorking || isInitializing || !hasTerraformDraft}
            >
              Generate Cleanup
            </button>
          </div>
        </header>

        <section className="service-card">
          <h2>Service Selection</h2>
          <div className="service-list">
            {SERVICE_OPTIONS.map((service) => (
              <label key={service}>
                <input
                  type="checkbox"
                  checked={selectedServices.includes(service)}
                  onChange={() => toggleService(service)}
                  disabled={isInitializing || isWorking}
                />
                {service}
              </label>
            ))}
          </div>
          <p className="requirements-preview">
            <strong>Session:</strong> {sessionId || "Not ready"}
            <br />
            <strong>Last intent:</strong> {resolvedIntent || "N/A"}
            <br />
            <strong>Review status:</strong> {hasReviewedDraft ? "Completed" : "Not run yet"}
            <br />
            <strong>Cleanup status:</strong> {cleanupScript.trim() ? "Generated" : "Not run yet"}
            <br />
            <strong>Current composed requirement:</strong> {requirementsPreview}
          </p>
          <div className="workflow-actions">
            <button
              className="btn"
              type="button"
              onClick={handleGenerateFromContext}
              disabled={isWorking || isInitializing}
            >
              Generate Draft
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={handleRunReview}
              disabled={isWorking || isInitializing || !hasTerraformDraft}
            >
              Run Review
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={handleRunCleanup}
              disabled={isWorking || isInitializing || !hasTerraformDraft}
            >
              Generate Cleanup
            </button>
          </div>
        </section>

        {errorMessage ? <div className="alert">{errorMessage}</div> : null}

        <main className="layout">
          <ChatPanel
            messages={messages}
            draftMessage={draftMessage}
            onDraftChange={setDraftMessage}
            onSend={handleSend}
            isWorking={isInitializing || isWorking}
            clarification={clarification}
          />
          <EditorPanel
            terraform={editorTerraform}
            onTerraformChange={setEditorTerraform}
            baselineTerraform={reviewedTerraform}
            changeSummary={changeSummary}
            cleanupScript={cleanupScript}
            sessionId={sessionId}
            diffLines={diffLines}
            isReviewing={isReviewing}
            onReviewDiff={handleReviewDiff}
            onResetToReviewed={handleResetTerraform}
            onFormat={handleFormatTerraform}
          />
        </main>
      </div>
    </div>
  );
}
