import { useEffect, useRef } from "react";

const QUICK_PROMPTS = [
  "Add one private app subnet",
  "Restrict SSH to 10.10.0.0/24",
  "Add an NSG for HTTPS traffic",
];

export default function ChatPanel({
  messages,
  draftMessage,
  onDraftChange,
  onSend,
  isWorking,
  clarification,
}) {
  const clarificationQuestions = Array.isArray(clarification?.clarification_questions)
    ? clarification.clarification_questions
    : Array.isArray(clarification?.questions)
      ? clarification.questions
      : [];
  const chatListRef = useRef(null);

  useEffect(() => {
    if (!chatListRef.current) {
      return;
    }
    chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
  }, [messages, clarificationQuestions.length]);

  return (
    <section className="panel chat-panel">
      <div className="panel-head">
        <h2>Requirements Chat</h2>
        <span className="pill">Assistant</span>
      </div>

      <div className="chat-list" ref={chatListRef}>
        {messages.map((msg) => (
          <article key={msg.id} className={`msg ${msg.role}`}>
            <p className="role">{msg.role === "assistant" ? "Solution" : "You"}</p>
            <p>{msg.content}</p>
          </article>
        ))}
      </div>

      {clarificationQuestions.length > 0 ? (
        <div className="clarify-box">
          <p className="clarify-title">Clarification needed before generation:</p>
          <ul>
            {clarificationQuestions.map((question, idx) => (
              <li key={`${question}-${idx}`}>{question}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="quick-row">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            className="chip"
            type="button"
            onClick={() => onSend(prompt)}
            disabled={isWorking}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="composer">
        <textarea
          value={draftMessage}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !isWorking) {
              event.preventDefault();
              onSend();
            }
          }}
          placeholder="Example: place compute in private subnet and allow HTTPS only."
          disabled={isWorking}
        />
        <button className="btn" type="button" onClick={() => onSend()} disabled={isWorking}>
          {isWorking ? "Working..." : "Send"}
        </button>
      </div>
    </section>
  );
}
