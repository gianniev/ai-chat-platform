type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatRequest = {
  message?: string;
  history?: ChatMessage[];
  conversation_id?: number;
  user_id?: number;
  persist?: boolean;
};

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ChatRequest;
    const userMessage = (body.message ?? "").trim();
    const history = Array.isArray(body.history) ? body.history : [];

    if (!userMessage) {
      return Response.json(
        { error: "El campo 'message' es obligatorio." },
        { status: 400 },
      );
    }

    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:18000";
    const upstream = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: userMessage,
        history,
        conversation_id: body.conversation_id,
        user_id: body.user_id,
        persist: body.persist,
      }),
      cache: "no-store",
    });

    if (!upstream.ok) {
      const data = await upstream.json().catch(() => null);
      return Response.json(
        {
          error: data?.detail ?? data?.error ?? "Error desde backend FastAPI.",
        },
        { status: upstream.status },
      );
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": upstream.headers.get("Cache-Control") ?? "no-cache",
        "X-Accel-Buffering": upstream.headers.get("X-Accel-Buffering") ?? "no",
      },
    });
  } catch {
    return Response.json(
      { error: "No se pudo conectar con el backend." },
      { status: 500 },
    );
  }
}
