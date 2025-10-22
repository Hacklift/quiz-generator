const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function saveUserToken(token: string) {
  const res = await fetch(`${API_BASE}/api/user/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });

  if (!res.ok) {
    throw new Error("Failed to save token");
  }

  return res.json();
}

export async function getUserToken(): Promise<string | null> {
  const res = await fetch(`${API_BASE}/api/user/token`, {
    method: "GET",
  });

  if (!res.ok) {
    return null;
  }

  const data = await res.json();
  return data.token || null;
}
