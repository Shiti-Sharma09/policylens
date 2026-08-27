"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getToken } from "@/lib/api";

export default function Home() {
  const [status, setStatus] = useState<string>("checking...");
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status === "ok" ? "OK" : "unexpected response"))
      .catch(() => setStatus("backend unreachable"));
    setLoggedIn(!!getToken());
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-bold">PolicyLens</h1>
      <p className="text-lg">
        Backend status: <span className="font-mono">{status}</span>
      </p>
      <div className="flex gap-4">
        {loggedIn ? (
          <Link href="/upload" className="underline">
            Your policies
          </Link>
        ) : (
          <>
            <Link href="/login" className="underline">
              Log in
            </Link>
            <Link href="/register" className="underline">
              Register
            </Link>
          </>
        )}
      </div>
    </main>
  );
}
