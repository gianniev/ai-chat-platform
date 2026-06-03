"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ModelAnalytics = {
  provider: string;
  model: string;
  total_requests: number;
  avg_latency_ms: number;
};

type AnalyticsResponse = {
  models: ModelAnalytics[];
};

type ChartRow = {
  provider: string;
  requests: number;
};

function formatLatency(value: number) {
  return `${Math.round(value)} ms`;
}

function titleCase(value: string) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : "Unknown";
}

export default function AnalyticsPage() {
  const [models, setModels] = useState<ModelAnalytics[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadAnalytics() {
      try {
        setIsLoading(true);
        setError(null);
        const response = await fetch("/api/analytics/models", { cache: "no-store" });
        const data = (await response.json()) as AnalyticsResponse & { error?: string };

        if (!response.ok) {
          throw new Error(data.error || "No se pudieron cargar las analiticas.");
        }

        if (isMounted) {
          setModels(Array.isArray(data.models) ? data.models : []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Error de conexion.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadAnalytics();

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(() => {
    const totalRequests = models.reduce((sum, item) => sum + item.total_requests, 0);
    const providers = new Set(models.map((item) => item.provider));
    const mostUsed = [...models].sort((a, b) => b.total_requests - a.total_requests)[0];
    const weightedLatency = models.reduce(
      (sum, item) => sum + item.avg_latency_ms * item.total_requests,
      0,
    );
    const averageLatency = totalRequests > 0 ? weightedLatency / totalRequests : 0;

    return {
      totalRequests,
      totalProviders: providers.size,
      mostUsedModel: mostUsed?.model ?? "No data",
      averageLatency,
    };
  }, [models]);

  const chartData = useMemo<ChartRow[]>(() => {
    const grouped = new Map<string, number>();
    for (const item of models) {
      grouped.set(item.provider, (grouped.get(item.provider) ?? 0) + item.total_requests);
    }
    return Array.from(grouped.entries()).map(([provider, requests]) => ({
      provider: titleCase(provider),
      requests,
    }));
  }, [models]);

  return (
    <main className="analyticsShell">
      <section className="analyticsHeader">
        <div>
          <p className="analyticsEyebrow">AI Chat Platform</p>
          <h1>Analytics Dashboard</h1>
          <p>Provider and model usage from anonymous backend metrics.</p>
        </div>
        <a className="analyticsBackLink" href="/">
          Back to chat
        </a>
      </section>

      {isLoading ? (
        <section className="analyticsState">Loading analytics...</section>
      ) : error ? (
        <section className="analyticsState analyticsStateError">{error}</section>
      ) : (
        <>
          <section className="analyticsSummaryGrid" aria-label="Analytics summary">
            <article className="analyticsCard">
              <span>Total Requests</span>
              <strong>{summary.totalRequests}</strong>
            </article>
            <article className="analyticsCard">
              <span>Total Providers</span>
              <strong>{summary.totalProviders}</strong>
            </article>
            <article className="analyticsCard">
              <span>Most Used Model</span>
              <strong title={summary.mostUsedModel}>{summary.mostUsedModel}</strong>
            </article>
            <article className="analyticsCard">
              <span>Average Latency</span>
              <strong>{formatLatency(summary.averageLatency)}</strong>
            </article>
          </section>

          <section className="analyticsContentGrid">
            <article className="analyticsPanel">
              <div className="analyticsPanelHeader">
                <h2>Requests by Provider</h2>
              </div>
              {chartData.length > 0 ? (
                <div className="analyticsChart">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                      <XAxis dataKey="provider" stroke="var(--text-muted)" tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--text-muted)" tickLine={false} axisLine={false} allowDecimals={false} />
                      <Tooltip
                        cursor={{ fill: "rgba(124,106,247,0.1)" }}
                        contentStyle={{
                          background: "var(--bg2)",
                          border: "1px solid var(--border)",
                          borderRadius: 8,
                          color: "var(--text)",
                        }}
                      />
                      <Bar dataKey="requests" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="analyticsEmpty">No analytics data yet.</div>
              )}
            </article>

            <article className="analyticsPanel">
              <div className="analyticsPanelHeader">
                <h2>Models</h2>
              </div>
              <div className="analyticsTableWrap">
                <table className="analyticsTable">
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Model</th>
                      <th>Requests</th>
                      <th>Avg Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {models.length > 0 ? (
                      models.map((item) => (
                        <tr key={`${item.provider}:${item.model}`}>
                          <td>{titleCase(item.provider)}</td>
                          <td>{item.model}</td>
                          <td>{item.total_requests}</td>
                          <td>{formatLatency(item.avg_latency_ms)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4}>No analytics data yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        </>
      )}
    </main>
  );
}
