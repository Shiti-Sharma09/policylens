"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, listPolicies, uploadPolicy, clearToken, type PolicySummary } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [policies, setPolicies] = useState<PolicySummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    setReady(true);
    refreshPolicies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshPolicies() {
    try {
      setPolicies(await listPolicies());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load policies");
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await uploadPolicy(file);
      await refreshPolicies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  if (!ready) return null;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-6 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your policies</h1>
        <div className="flex gap-4">
          <a href="/chat" className="text-sm underline">
            Ask a question
          </a>
          <button onClick={handleLogout} className="text-sm underline">
            Log out
          </button>
        </div>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded border-2 border-dashed p-8 text-center">
        <span>{uploading ? "Uploading and processing..." : "Click to upload a policy PDF"}</span>
        <input type="file" accept="application/pdf" onChange={handleFileChange} disabled={uploading} className="hidden" />
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="flex flex-col gap-2">
        {policies.map((p) => (
          <li key={p.id} className="rounded border p-3">
            <p className="font-medium">{p.filename}</p>
            <p className="text-sm text-gray-500">
              {p.insurer ?? "Unknown insurer"} · {p.structural_type ?? "Unclassified"} · {p.chunk_count} chunks ·{" "}
              {p.indexed ? "indexed" : "indexing..."}
            </p>
          </li>
        ))}
        {policies.length === 0 && <p className="text-sm text-gray-500">No policies uploaded yet.</p>}
      </ul>
    </main>
  );
}
