/* replay-shim.js — used ONLY by the static (Vercel) copy of the site. It answers the handful of GET/POST calls the
   landing page and the dashboard make from /static/recording.json, which was captured from the real local stack
   by scripts/record_playback.py. Anything it doesn't recognise falls through to the network (and fails, honestly). */
(function () {
  const realFetch = window.fetch.bind(window);
  let rec = null;
  const load = realFetch("/static/recording.json").then((r) => r.json()).then((j) => (rec = j));
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  const READONLY = { error: "This is a recorded snapshot, so it is read-only. Run the project locally (see the README) to change things.", recorded: true };

  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : input.url;
    const path = url.replace(location.origin, "").split("?")[0];
    const method = ((init && init.method) || "GET").toUpperCase();
    if (!path.startsWith("/api/")) return realFetch(input, init);
    await load;
    if (path === "/api/health") return json({ ...rec.health, recorded: true, recorded_at: rec.recorded_at });
    let m;
    if ((m = path.match(/^\/api\/dashboard\/(\w+)$/))) {
      const d = rec.dashboard[m[1]];
      if (!d) return json({ error: "No snapshot for that brand." }, 404);
      return d._status ? json({ error: d.error, decision: d.decision, recorded: true }, d._status) : json(d);
    }
    if ((m = path.match(/^\/api\/tickets\/([\w-]+)\/thread$/))) return rec.threads[m[1]] ? json(rec.threads[m[1]]) : json({ error: "No snapshot of that chat." }, 404);
    if (path.startsWith("/api/tickets/") && method === "POST") return json(READONLY, 403);
    if (path === "/api/sample-csv") return new Response(rec.csv.clean, { headers: { "Content-Type": "text/csv" } });
    if (path === "/api/ingest" && method === "POST") {
      const body = (init && init.body) || "";
      if (body.includes("TV-55-X")) return json(rec.ingest_check.messy);
      if (body.trim() === rec.csv.clean.trim()) return json(rec.ingest_check.clean);
      return json({ error: "Checking your own file needs the running stack. This static copy only replays the two sample files. See the README to run it locally." }, 422);
    }
    return json(READONLY, 503);
  };
})();
