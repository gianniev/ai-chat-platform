function getBackendUrl() {
  return process.env.BACKEND_URL ?? "http://localhost:18000";
}

export async function GET() {
  try {
    const upstream = await fetch(`${getBackendUrl()}/analytics/models`, {
      method: "GET",
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
