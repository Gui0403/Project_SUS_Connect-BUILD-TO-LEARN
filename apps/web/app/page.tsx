const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getApiStatus(): Promise<string> {
  try {
    // Server Component: roda dentro do container "web", então usa o host "api" da rede do Compose.
    const res = await fetch("http://api:8000/health/db", { cache: "no-store" });
    const data = await res.json();
    return res.ok ? `API e banco OK (${data.database})` : "API respondeu com erro";
  } catch {
    return "API indisponível";
  }
}

export default async function Home() {
  const status = await getApiStatus();
  return (
    <main className="mx-auto max-w-2xl p-10">
      <h1 className="text-3xl font-bold">SUS Connect</h1>
      <p className="mt-2 text-slate-600">Projeto Build to Learn — Dia 1</p>
      <div className="mt-6 rounded-lg border bg-white p-4">
        <p className="text-sm text-slate-500">Status do backend</p>
        <p className="font-medium">{status}</p>
        <p className="mt-2 text-xs text-slate-400">Swagger: {API_URL}/docs</p>
      </div>
    </main>
  );
}
