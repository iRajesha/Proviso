const JSON_HEADERS = {
  "Content-Type": "application/json",
};

async function parseJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.toLowerCase().includes("application/json");
  if (!isJson) {
    return null;
  }
  return response.json();
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, options);
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    const error = new Error(data?.detail || `${path} failed with status ${response.status}`);
    error.kind = "http";
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

export async function createChatSession(services = []) {
  return requestJson("/api/v1/chat/sessions", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ services }),
  });
}

export async function getChatSession(sessionId) {
  return requestJson(`/api/v1/chat/sessions/${sessionId}`, {
    method: "GET",
  });
}

export async function sendChatMessage({
  sessionId,
  message,
  intent = "auto",
  services = null,
}) {
  return requestJson(`/api/v1/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({
      message,
      intent,
      services,
    }),
  });
}

export async function reviewTerraformDiff(original, modified) {
  return requestJson("/api/v1/review/diff", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ original, modified }),
  });
}
