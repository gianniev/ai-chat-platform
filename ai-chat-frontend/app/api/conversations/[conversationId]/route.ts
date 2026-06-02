type UpdateConversationRequest = {
  title?: string;
  user_id?: number;
};

type RouteContext = {
  params: Promise<{ conversationId: string }>;
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

export async function PATCH(request: Request, context: RouteContext) {
  try {
    const { conversationId } = await context.params;
    const body = (await request.json()) as UpdateConversationRequest;
    const upstream = await fetch(`${getBackendUrl()}/conversations/${conversationId}`, {
      method: "PATCH",
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

export async function DELETE(request: Request, context: RouteContext) {
  try {
    const { conversationId } = await context.params;
    const url = new URL(request.url);
    const upstream = await fetch(
      `${getBackendUrl()}/conversations/${conversationId}?${url.searchParams}`,
      {
        method: "DELETE",
        cache: "no-store",
      },
    );

    return forwardJson(upstream);
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend." },
      { status: 500 },
    );
  }
}
