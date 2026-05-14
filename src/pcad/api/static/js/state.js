const initialState = {
  session: null,
  accounts: [],
  currentAccountId: null,
  currentArtifactId: null,
  artifactsByAccount: {},
  alertsByAccount: {},
  fakeNotesByAccount: {},
  threads: [],
  currentThreadId: null,
  messagesByThread: {},
  isStreaming: false,
  streamingThreadId: null,
  streamingTokens: "",
  streamingCitations: [],
  lastError: null,
  rateLimitedUntil: null,
  route: { name: "accounts", params: {} },
};

const subscribers = new Map();

export const state = {
  data: { ...initialState },

  get(key) {
    return this.data[key];
  },

  set(key, value) {
    this.data = { ...this.data, [key]: value };
    notify(key, value);
    notify("*", this.data);
  },

  update(key, updater) {
    this.set(key, updater(this.get(key)));
  },

  subscribe(key, callback) {
    const bucket = subscribers.get(key) || new Set();
    bucket.add(callback);
    subscribers.set(key, bucket);
    return () => bucket.delete(callback);
  },
};

function notify(key, value) {
  for (const callback of subscribers.get(key) || []) {
    callback(value, state.data);
  }
}
