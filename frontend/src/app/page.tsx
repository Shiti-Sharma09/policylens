"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState<string>("checking...");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status === "ok" ? "OK" : "unexpected response"))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-bold">PolicyLens</h1>
      <p className="text-lg">
        Backend status: <span className="font-mono">{status}</span>
      </p>
    </main>
  );
}
