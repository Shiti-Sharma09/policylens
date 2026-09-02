const API_URL = process.env.NEXT_PUBLIC_API_URL;
const TOKEN_KEY = "policylens_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg).join(", ");
    }
  } catch {
    // response wasn't JSON - fall through to generic message
  }
  return `Request failed (${res.status})`;
}

export async function register(email: string, password: string): Promise<{ id: number; email: string }> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  const data = await res.json();
  return data.access_token as string;
}

export interface PolicySummary {
  id: number;
  filename: string;
  structural_type: string | null;
  insurer: string | null;
  is_reference_doc: boolean;
  chunk_count: number;
  indexed: boolean;
  tenure_years: number | null;
}

export async function listPolicies(): Promise<PolicySummary[]> {
  const token = getToken();
  const res = await fetch(`${API_URL}/upload/policies`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store", // indexed status changes in the background; never serve a stale cached copy
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export async function uploadPolicy(file: File): Promise<PolicySummary> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/upload/policy`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export interface Citation {
  chunk_text: string;
  section_hint: string | null;
  chunk_index: number;
  score: number;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  cached: boolean;
}

export async function askQuestion(policyId: number, question: string): Promise<AskResponse> {
  const token = getToken();
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ policy_id: policyId, question }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  return res.json();
}

export interface StreamResult {
  citations: Citation[];
  cached: boolean;
}

/**
 * Streaming variant of askQuestion(). Uses fetch's ReadableStream instead of
 * EventSource because EventSource can't send the Authorization header or a POST
 * body - the backend speaks Server-Sent Events (`data: {...}\n\n` lines) over a
 * plain POST response instead. `onToken` fires once per answer piece as it
 * arrives; the returned promise resolves with citations once the `done` event
 * arrives.
 */
export async function askQuestionStream(
  policyId: number,
  question: string,
  onToken: (text: string) => void
): Promise<StreamResult> {
  const token = getToken();
  const res = await fetch(`${API_URL}/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ policy_id: policyId, question }),
  });
  if (!res.ok) throw new Error(await parseErrorDetail(res));
  if (!res.body) throw new Error("Streaming isn't supported in this browser");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: StreamResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line; the last split part may be an
    // incomplete event still being received, so keep it in the buffer.
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      const line = event.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = JSON.parse(line.slice("data: ".length));
      if (payload.type === "token") {
        onToken(payload.text as string);
      } else if (payload.type === "done") {
        result = { citations: payload.citations as Citation[], cached: payload.cached as boolean };
      }
    }
  }

  return result ?? { citations: [], cached: false };
}
