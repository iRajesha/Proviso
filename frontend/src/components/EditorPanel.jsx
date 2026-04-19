function diffStats(diffLines) {
  let added = 0;
  let removed = 0;
  for (const line of diffLines) {
    if (line.startsWith("+") && !line.startsWith("+++")) {
      added += 1;
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      removed += 1;
    }
  }
  return { added, removed, total: added + removed };
}

export default function EditorPanel({
  terraform,
  onTerraformChange,
  baselineTerraform,
  changeSummary,
  cleanupScript,
  sessionId,
  diffLines,
  isReviewing,
  onReviewDiff,
  onResetToReviewed,
  onFormat,
}) {
  const stats = diffStats(diffLines);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Terraform Editor</h2>
        <span className="pill neutral">{terraform.split("\n").length} lines</span>
      </div>

      <div className="toolbar">
        <span className="tab active">main.tf</span>
        <span className="tab">variables.tf</span>
        <span className="tab">outputs.tf</span>
        <button type="button" className="tab action" onClick={onFormat}>
          format
        </button>
        <button type="button" className="tab action" onClick={onResetToReviewed}>
          reset
        </button>
        <button type="button" className="tab action" onClick={onReviewDiff} disabled={isReviewing}>
          {isReviewing ? "reviewing..." : "review diff"}
        </button>
      </div>

      <textarea
        className="code"
        value={terraform}
        onChange={(event) => onTerraformChange(event.target.value)}
        spellCheck={false}
      />

      <div className="meta-grid">
        <div className="meta-card">
          <h3>Session</h3>
          <p>{sessionId || "No generation session yet"}</p>
        </div>
        <div className="meta-card">
          <h3>Diff Stats</h3>
          <p>
            {stats.total > 0
              ? `${stats.total} changes (${stats.added} additions, ${stats.removed} removals)`
              : "No diff computed yet"}
          </p>
        </div>
      </div>

      <div className="summary">
        <h3>Change summary from reviewer</h3>
        <pre>{changeSummary || "No summary available yet."}</pre>
      </div>

      <div className="summary">
        <h3>Cleanup script preview</h3>
        <pre>{cleanupScript || "No cleanup script generated yet."}</pre>
      </div>

      <div className="summary">
        <h3>Diff output</h3>
        <pre>
          {baselineTerraform
            ? diffLines.length > 0
              ? diffLines.join("\n")
              : "Run review diff to compare reviewed terraform with editor content."
            : "Generate infrastructure first to establish baseline."}
        </pre>
      </div>
    </section>
  );
}
