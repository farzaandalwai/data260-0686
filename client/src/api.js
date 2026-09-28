const API_BASE = "http://127.0.0.1:8686";

async function request(path, options) {
  const settings = options || {};
  const headers = { ...(settings.headers || {}) };
  if (settings.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(API_BASE + path, {
    method: settings.method || "GET",
    headers,
    body: settings.body,
    credentials: "include",
  });
  const text = await response.text();
  let data = null;
  if (text) {
    data = JSON.parse(text);
  }
  if (!response.ok) {
    let message = "Request failed";
    if (data && typeof data.detail === "string") {
      message = data.detail;
    }
    throw new Error(message);
  }
  return data;
}

export function getJson(path) {
  return request(path);
}

export function sendJson(path, method, body) {
  return request(path, {
    method,
    body: JSON.stringify(body),
  });
}

export function postEmpty(path) {
  return request(path, { method: "POST" });
}
