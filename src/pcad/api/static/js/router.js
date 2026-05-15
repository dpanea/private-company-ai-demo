export function parseRoute(hash = window.location.hash) {
  const route = hash.replace(/^#/, "") || "/";
  const parts = route.split("/").filter(Boolean);

  if (parts.length === 0) return { name: "memory", params: {} };
  if (parts[0] === "threads" && parts[1]) {
    return { name: "thread", params: { threadId: parts[1] } };
  }
  if (parts[0] === "artifacts" && parts[1]) {
    return { name: "artifact", params: { artifactId: parts[1] } };
  }
  if (parts[0] === "accounts" && parts[1] && parts[2] === "threads" && parts[3]) {
    return { name: "account_thread", params: { accountId: parts[1], threadId: parts[3] } };
  }
  if (parts[0] === "accounts" && parts[1] && parts[2] === "artifacts" && parts[3]) {
    return { name: "account_artifact", params: { accountId: parts[1], artifactId: parts[3] } };
  }
  if (parts[0] === "accounts" && parts[1]) {
    return { name: "account", params: { accountId: parts[1] } };
  }
  return { name: "not_found", params: {} };
}

export function navigate(path) {
  window.location.hash = path.startsWith("#") ? path.slice(1) : path;
}

export function accountPath(accountId) {
  return "#/";
}

export function threadPath(accountId, threadId) {
  return `#/threads/${encodeURIComponent(threadId)}`;
}

export function artifactPath(accountId, artifactId) {
  return `#/artifacts/${encodeURIComponent(artifactId)}`;
}
