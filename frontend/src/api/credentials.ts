// Keys live in sessionStorage so they are dropped when the tab closes.
const API_KEY = "csa.apiKey";
const APPROVER_KEY = "csa.refundApproverKey";

export type Credentials = {
  apiKey: string;
  approverKey: string;
};

function read(name: string): string {
  try {
    return window.sessionStorage.getItem(name) ?? "";
  } catch {
    return "";
  }
}

function write(name: string, value: string) {
  try {
    if (value) {
      window.sessionStorage.setItem(name, value);
    } else {
      window.sessionStorage.removeItem(name);
    }
  } catch {
    // Storage can be unavailable (private mode, disabled cookies); requests then go without a key.
  }
}

export function loadCredentials(): Credentials {
  return { apiKey: read(API_KEY), approverKey: read(APPROVER_KEY) };
}

export function saveCredentials(credentials: Credentials) {
  write(API_KEY, credentials.apiKey.trim());
  write(APPROVER_KEY, credentials.approverKey.trim());
}

export function clearCredentials() {
  saveCredentials({ apiKey: "", approverKey: "" });
}

/** Key for regular business calls. An approver key is accepted there too. */
export function businessKey(): string {
  const { apiKey, approverKey } = loadCredentials();
  return apiKey || approverKey;
}

/** Key for approve, reject and execute. A plain API key gets 403 from the server. */
export function approverKeyOrFallback(): string {
  const { apiKey, approverKey } = loadCredentials();
  return approverKey || apiKey;
}
