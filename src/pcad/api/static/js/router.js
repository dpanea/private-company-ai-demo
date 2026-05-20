export function parseRoute(hash = window.location.hash) {
  const route = hash.replace(/^#/, "") || "/";
  const parts = route.split("/").filter(Boolean);

  if (parts.length === 0) return { name: "memory", params: {} };
  if (parts[0] === "threads" && parts[1]) {
    return { name: "thread", params: { threadId: decodeSegment(parts[1]) } };
  }
  if (parts[0] === "artifacts" && parts[1]) {
    return { name: "artifact", params: { artifactId: decodeSegment(parts[1]) } };
  }
  if (parts[0] === "accounts" && parts[1] && parts[2] === "threads" && parts[3]) {
    return { name: "account_thread", params: { accountId: decodeSegment(parts[1]), threadId: decodeSegment(parts[3]) } };
  }
  if (parts[0] === "accounts" && parts[1] && parts[2] === "artifacts" && parts[3]) {
    return { name: "account_artifact", params: { accountId: decodeSegment(parts[1]), artifactId: decodeSegment(parts[3]) } };
  }
  if (parts[0] === "accounts" && parts[1]) {
    return { name: "account", params: { accountId: decodeSegment(parts[1]) } };
  }
  return { name: "not_found", params: {} };
}

export function navigate(path) {
  window.location.hash = path.startsWith("#") ? path.slice(1) : path;
}

export function accountPath(accountId) {
  return accountId ? `#/accounts/${encodeURIComponent(accountId)}` : "#/";
}

export function threadPath(accountId, threadId) {
  if (accountId) {
    return `#/accounts/${encodeURIComponent(accountId)}/threads/${encodeURIComponent(threadId)}`;
  }
  return `#/threads/${encodeURIComponent(threadId)}`;
}

export function artifactPath(accountId, artifactId) {
  if (accountId) {
    return `#/accounts/${encodeURIComponent(accountId)}/artifacts/${encodeURIComponent(artifactId)}`;
  }
  return `#/artifacts/${encodeURIComponent(artifactId)}`;
}

function decodeSegment(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
