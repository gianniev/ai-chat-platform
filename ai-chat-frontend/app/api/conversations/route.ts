type CreateConversationRequest = {
  title?: string;
  user_id?: number;
};

function getBackendUrl() {
  return process.env.BACKEND_URL ?? "http://localhost:18000";
}

async function forwardJson(upstream: Response) {
  const data = await upstream.json();

  if (!upstream.ok) {
    return Response.json(
      { error: data?.detail ?? data?.error ?? "Error desde backend FastAPI." },
      { status: upstream.status },
    );
  }

  return Response.json(data, { status: upstream.status });
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const upstream = await fetch(`${getBackendUrl()}/conversations?${url.searchParams}`, {
      cache: "no-store",
    });

    return forwardJson(upstream);
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend." },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as CreateConversationRequest;
    const upstream = await fetch(`${getBackendUrl()}/conversations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    return forwardJson(upstream);
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend." },
      { status: 500 },
    );
  }
}
