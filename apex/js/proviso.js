/**
 * Proviso — main APEX integration script
 * Loaded as a Static Application File on the APEX app.
 */

/* ── Monaco Diff Editor ─────────────────────────────────────── */
require.config({
  paths: {
    vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.47.0/min/vs",
  },
});

let diffEditor = null;

function renderDiffEditor(originalCode, modifiedCode) {
  const container = document.getElementById("diffEditorContainer");
  if (!container) return;

  if (diffEditor) {
    diffEditor.dispose();
  }

  require(["vs/editor/editor.main"], function () {
    diffEditor = monaco.editor.createDiffEditor(container, {
      automaticLayout: true,
      readOnly: true,
      renderSideBySide: true,
      theme: "vs-dark",
    });

    diffEditor.setModel({
      original: monaco.editor.createModel(originalCode, "hcl"),
      modified: monaco.editor.createModel(modifiedCode, "hcl"),
    });
  });
}

/* ── Mermaid Diagram ─────────────────────────────────────────── */
function renderMermaidDiagram(mermaidSrc) {
  const container = document.getElementById("mermaidContainer");
  if (!container) return;
  container.innerHTML =
    '<div class="mermaid">' + apex.util.escapeHTMLAttr(mermaidSrc) + "</div>";
  mermaid.init(undefined, container.querySelectorAll(".mermaid"));
}

/* ── Generate Button Handler ─────────────────────────────────── */
function provisoGenerate() {
  const requirements = apex.item("P1_REQUIREMENTS").getValue();
  const servicesRaw = apex.item("P1_SERVICES").getValue(); // shuttle returns colon-separated
  const services = servicesRaw ? servicesRaw.split(":").filter(Boolean) : [];

  if (!requirements.trim()) {
    apex.message.showErrors([
      { type: "error", location: "inline", pageItem: "P1_REQUIREMENTS", message: "Requirements cannot be empty." },
    ]);
    return;
  }

  apex.item("P1_GENERATE_BTN").disable();
  apex.message.clearErrors();
  document.getElementById("loadingSpinner").style.display = "block";

  apex.server.process("GENERATE_INFRA", {
    x01: requirements,
    x02: services.join(","),
  }, {
    success: function (data) {
      document.getElementById("loadingSpinner").style.display = "none";
      apex.item("P1_GENERATE_BTN").enable();

      const result = typeof data === "string" ? JSON.parse(data) : data;

      apex.item("P1_GENERATED_TF").setValue(result.generated_terraform || "");
      apex.item("P1_REVIEWED_TF").setValue(result.reviewed_terraform || "");
      apex.item("P1_CHANGE_SUMMARY").setValue(result.change_summary || "");
      apex.item("P1_CLEANUP_SCRIPT").setValue(result.cleanup_script || "");
      apex.item("P1_SESSION_ID").setValue(result.session_id || "");

      renderDiffEditor(
        result.generated_terraform || "",
        result.reviewed_terraform || ""
      );

      if (result.mermaid_diagram) {
        renderMermaidDiagram(result.mermaid_diagram);
      }
    },
    error: function (jqXHR) {
      document.getElementById("loadingSpinner").style.display = "none";
      apex.item("P1_GENERATE_BTN").enable();
      apex.message.showErrors([
        { type: "error", location: "page", message: "Generation failed: " + jqXHR.statusText },
      ]);
    },
  });
}

/* ── Save to Gold Library ────────────────────────────────────── */
function provisoSave() {
  const title = apex.item("P1_TITLE").getValue();
  const useCase = apex.item("P1_REQUIREMENTS").getValue();
  const terraformCode = apex.item("P1_REVIEWED_TF").getValue();
  const cleanupScript = apex.item("P1_CLEANUP_SCRIPT").getValue();
  const changeSummary = apex.item("P1_CHANGE_SUMMARY").getValue();
  const services = apex.item("P1_SERVICES").getValue().split(":").filter(Boolean);

  if (!title.trim() || !terraformCode.trim()) {
    apex.message.showErrors([
      { type: "error", location: "page", message: "Title and reviewed Terraform are required to save." },
    ]);
    return;
  }

  apex.server.process("SAVE_SCRIPT", {
    x01: JSON.stringify({ title, use_case: useCase, services, terraform_code: terraformCode, cleanup_script: cleanupScript, change_summary: changeSummary }),
  }, {
    success: function (data) {
      apex.message.showPageSuccess("Script saved to Gold Library! ID: " + data.id);
    },
    error: function () {
      apex.message.showErrors([{ type: "error", location: "page", message: "Failed to save script." }]);
    },
  });
}

/* ── Gold Library Search ─────────────────────────────────────── */
function provisoSearch() {
  const query = apex.item("P2_SEARCH_QUERY").getValue();
  if (!query.trim()) return;

  apex.server.process("SEARCH_SCRIPTS", { x01: query }, {
    success: function (data) {
      const results = typeof data === "string" ? JSON.parse(data) : data;
      const tbody = document.getElementById("searchResultsBody");
      tbody.innerHTML = "";
      results.forEach(function (r) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" + apex.util.escapeHTML(r.id) + "</td>" +
          "<td><a href='#' onclick='provisoLoadScript(" + r.id + ")'>" + apex.util.escapeHTML(r.title) + "</a></td>" +
          "<td>" + apex.util.escapeHTML(r.use_case.substring(0, 120)) + "…</td>" +
          "<td>" + (r.score * 100).toFixed(1) + "%</td>";
        tbody.appendChild(tr);
      });
    },
  });
}

function provisoLoadScript(scriptId) {
  apex.server.process("GET_SCRIPT", { x01: scriptId }, {
    success: function (data) {
      const s = typeof data === "string" ? JSON.parse(data) : data;
      apex.item("P2_TF_CODE").setValue(s.terraform_code);
      apex.item("P2_CLEANUP_CODE").setValue(s.cleanup_script);
    },
  });
}
