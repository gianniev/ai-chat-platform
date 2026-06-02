type FeedbackRequest = {
  rating?: "up" | "down";
  client_message_id?: string;
  client_thread_id?: string;
  model?: string;
  comment?: string;
};

function getBackendUrl() {
  return process.env.BACKEND_URL ?? "http://localhost:18000";
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as FeedbackRequest;

    if (body.rating !== "up" && body.rating !== "down") {
      return Response.json({ error: "rating invalido." }, { status: 400 });
    }

    const upstream = await fetch(`${getBackendUrl()}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
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
