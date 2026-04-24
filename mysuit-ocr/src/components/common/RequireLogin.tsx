"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { hasStoredLogin } from "@/lib/login";

type RequireLoginProps = {
  children: React.ReactNode;
};

export default function RequireLogin({ children }: RequireLoginProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    const ok = hasStoredLogin();
    setLoggedIn(ok);
    setReady(true);

    if (!ok) {
      router.replace("/login");
    }
  }, [router]);

  if (!ready) {
    return null;
  }

  if (!loggedIn) {
    return null;
  }

  return <>{children}</>;
}