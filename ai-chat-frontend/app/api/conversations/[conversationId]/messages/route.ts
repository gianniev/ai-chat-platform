type RouteContext = {
  params: Promise<{ conversationId: string }>;
};

function getBackendUrl() {
  return process.env.BACKEND_URL ?? "http://localhost:18000";
}

export async function GET(request: Request, context: RouteContext) {
  try {
    const { conversationId } = await context.params;
    const url = new URL(request.url);
    const upstream = await fetch(
      `${getBackendUrl()}/conversations/${conversationId}/messages?${url.searchParams}`,
      { cache: "no-store" },
    );
    const data = await upstream.json();

    if (!upstream.ok) {
      return Response.json(
        { error: data?.detail ?? data?.error ?? "Error desde backend FastAPI." },
        { status: upstream.status },
      );
    }

    return Response.json(data, { status: 200 });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend." },
      { status: 500 },
    );
  }
}
