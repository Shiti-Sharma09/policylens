"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, listPolicies, askQuestionStream, type PolicySummary, type Citation } from "@/lib/api";

interface Turn {
  question: string;
  answer: string;
  citations: Citation[];
  cached: boolean;
}

export default function ChatPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [policies, setPolicies] = useState<PolicySummary[]>([]);
  const [policyId, setPolicyId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    setReady(true);

    let cancelled = false;
    let poll: ReturnType<typeof setInterval> | null = null;

    async function refreshPolicies() {
      try {
        const all = await listPolicies();
        if (cancelled) return;
        setPolicies(all);
        setPolicyId((current) => {
          if (current && all.some((p) => p.id === current)) return current;
          return all.find((p) => p.indexed)?.id ?? current;
        });
        // Stop polling once nothing is still indexing - no point refreshing further.
        if (poll && all.every((p) => p.indexed)) {
          clearInterval(poll);
          poll = null;
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load policies");
      }
    }

    refreshPolicies();
    // Some policies may still be indexing in the background - keep the list fresh
    // instead of requiring a manual page reload to see them become selectable.
    poll = setInterval(refreshPolicies, 15000);

    return () => {
      cancelled = true;
      if (poll) clearInterval(poll);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!policyId || !question.trim() || asking) return;

    setError(null);
    setAsking(true);
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);

    const askedQuestion = question;
    setQuestion("");

    // Add the turn immediately with an empty answer, then fill it in token-by-token
    // as the stream arrives - this is what drives the typing animation below.
    const turnIndex = turns.length;
    setTurns((prev) => [...prev, { question: askedQuestion, answer: "", citations: [], cached: false }]);

    try {
      const { citations, cached } = await askQuestionStream(policyId, askedQuestion, (text) => {
        setTurns((prev) => {
          const next = [...prev];
          next[turnIndex] = { ...next[turnIndex], answer: next[turnIndex].answer + text };
          return next;
        });
      });
      setTurns((prev) => {
        const next = [...prev];
        next[turnIndex] = { ...next[turnIndex], citations, cached };
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get an answer");
      setTurns((prev) => prev.slice(0, turnIndex));
    } finally {
      setAsking(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }

  if (!ready) return null;

  const selectedPolicy = policies.find((p) => p.id === policyId);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Ask your policy</h1>
        <a href="/upload" className="text-sm underline">
          Manage policies
        </a>
      </div>

      <select
        value={policyId ?? ""}
        onChange={(e) => setPolicyId(Number(e.target.value))}
        className="rounded border bg-black px-3 py-2 text-white"
      >
        <option value="" disabled className="bg-black text-white">
          Select a policy
        </option>
        {policies.map((p) => (
          <option key={p.id} value={p.id} disabled={!p.indexed} className="bg-black text-white">
            {p.filename} {p.insurer ? `(${p.insurer})` : ""} {p.indexed ? "" : "- indexing..."}
          </option>
        ))}
      </select>

      {selectedPolicy && !selectedPolicy.indexed && (
        <p className="text-sm text-amber-600">
          This policy is still being indexed - questions can&apos;t be answered until it finishes (this can
          take a few minutes for a full policy).
        </p>
      )}

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {turns.length === 0 && (
          <p className="text-sm text-gray-500">
            Ask something like &ldquo;is windshield damage covered?&rdquo; or &ldquo;what is covered under
            third party liability?&rdquo;
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-2 rounded border p-3">
            <p className="font-medium">{turn.question}</p>
            <p className="whitespace-pre-wrap text-sm">
              {turn.answer}
              {asking && i === turns.length - 1 && <span className="animate-pulse">▋</span>}
            </p>
            {turn.cached && <p className="text-xs text-gray-400">(answered instantly from cache)</p>}
            {turn.citations.length > 0 && (
              <div className="flex flex-col gap-1">
                <p className="text-xs font-medium text-gray-500">Sources:</p>
                {turn.citations.map((c, j) => {
                  const key = `${i}-${j}`;
                  return (
                    <div key={key}>
                      <button
                        onClick={() => setExpanded(expanded === key ? null : key)}
                        className="text-left text-xs underline"
                      >
                        {c.section_hint ?? `Chunk ${c.chunk_index}`} (score {c.score.toFixed(2)})
                      </button>
                      {expanded === key && (
                        <p className="mt-1 rounded bg-gray-50 p-2 text-xs text-gray-700">{c.chunk_text}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {asking && turns[turns.length - 1]?.answer === "" && (
        <p className="text-sm text-gray-500">
          Thinking... ({elapsed}s) - the first words can take a while to arrive on this hardware, please wait.
        </p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about this policy..."
          disabled={asking || !policyId}
          className="flex-1 rounded border px-3 py-2"
        />
        <button
          type="submit"
          disabled={asking || !policyId || !question.trim()}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          {asking ? "Asking..." : "Ask"}
        </button>
      </form>
    </main>
  );
}
