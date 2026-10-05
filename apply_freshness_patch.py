
#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server" / "discord_notifier.py"
DASH = ROOT / "server" / "dashboard.html"

if not SERVER.is_file() or not DASH.is_file():
    raise SystemExit(
        "Jalankan script dari root repository "
        "(folder yang berisi server/discord_notifier.py dan server/dashboard.html)."
    )

def replace_once(path, old, new, label):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: pola ditemukan {count}x (harus tepat 1x).")
    backup = path.with_name(path.name + ".freshness.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

replace_once(
    SERVER,
    '''POLL_ENABLED = os.environ.get("POLL_ENABLED", "1").strip().lower() not in ("0", "false", "no", "")

# Jitter kecil''',
    '''POLL_ENABLED = os.environ.get("POLL_ENABLED", "1").strip().lower() not in ("0", "false", "no", "")

# Perkiraan interval laporan browser extension / Worker saat direct poller dimatikan.
WORKER_INTERVAL = int(os.environ.get("WORKER_INTERVAL", "30"))

# Telemetry runtime poller untuk ditampilkan ke dashboard.
poll_runtime_lock = threading.Lock()
poll_runtime = {
    "cycle_started": None,
    "last_cycle": None,
    "next_at": None,
    "blocked": False,
    "backoff": 0,
    "sleep_for": None,
    "profile": None,
}

# Jitter kecil''',
    "server telemetry declaration",
)

replace_once(
    SERVER,
    '''def poller_info():
    return {
        "enabled": POLL_ENABLED,
        "mode": "direct" if POLL_ENABLED else "worker",
        "status": poll_status,
    }''',
    '''def poller_info():
    with poll_runtime_lock:
        runtime = dict(poll_runtime)

    return {
        "enabled": POLL_ENABLED,
        "mode": "direct" if POLL_ENABLED else "worker",
        "interval": POLL_INTERVAL if POLL_ENABLED else WORKER_INTERVAL,
        "worker_interval": WORKER_INTERVAL,
        "ui_refresh": 10,
        "next_at": runtime.get("next_at"),
        "cycle_started": runtime.get("cycle_started"),
        "last_cycle": runtime.get("last_cycle"),
        "blocked": runtime.get("blocked", False),
        "backoff": runtime.get("backoff", 0),
        "sleep_for": runtime.get("sleep_for"),
        "profile": runtime.get("profile"),
        "status": poll_status,
    }''',
    "server poller_info",
)

replace_once(
    SERVER,
    '''        events[code] = {"name": name, "updated": last_report.get(code),
                            "sale": sale_state.get(code, "open"), "lanes": lanes}''',
    '''        updated = last_report.get(code)
        with poll_runtime_lock:
            direct_next = poll_runtime.get("next_at")

        expected_next = (
            direct_next if POLL_ENABLED and direct_next
            else (updated + WORKER_INTERVAL if updated else None)
        )

        events[code] = {
            "name": name,
            "updated": updated,
            "next_at": expected_next,
            "source": "direct-poller" if POLL_ENABLED else "browser-extension/worker",
            "sale": sale_state.get(code, "open"),
            "lanes": lanes,
        }''',
    "server event freshness metadata",
)

replace_once(
    SERVER,
    '''    return {
        "now": now, "started": START_TIME, "uptime": uptime,
        "components": comps,
        "requests": {"total": total, "errors": errors},
        "poller": {"enabled": POLL_ENABLED, "interval": POLL_INTERVAL},
        "stale_after": STALE_SECONDS,
    }''',
    '''    return {
        "now": now, "started": START_TIME, "uptime": uptime,
        "components": comps,
        "requests": {"total": total, "errors": errors},
        "poller": poller_info(),
        "stale_after": STALE_SECONDS,
    }''',
    "server health snapshot",
)

replace_once(
    SERVER,
    '''    while True:
        started = time.time()
        blocked = False

        try:''',
    '''    while True:
        started = time.time()
        blocked = False

        with poll_runtime_lock:
            poll_runtime.update({
                "cycle_started": started,
                "last_cycle": started,
                "next_at": None,
                "blocked": False,
                "backoff": backoff,
                "sleep_for": None,
                "profile": profiles[profile_idx],
            })

        try:''',
    "server poll loop start telemetry",
)

replace_once(
    SERVER,
    '''        elapsed = time.time() - started
        jitter = random.uniform(0, POLL_JITTER_MAX)
        sleep_for = max(5.0, current_poll_interval() - elapsed + jitter + backoff)

        if blocked:''',
    '''        elapsed = time.time() - started
        jitter = random.uniform(0, POLL_JITTER_MAX)
        sleep_for = max(5.0, current_poll_interval() - elapsed + jitter + backoff)

        with poll_runtime_lock:
            poll_runtime.update({
                "last_cycle": time.time(),
                "next_at": time.time() + sleep_for,
                "blocked": blocked,
                "backoff": backoff,
                "sleep_for": sleep_for,
                "profile": profiles[profile_idx],
            })

        if blocked:''',
    "server poll loop next telemetry",
)

replace_once(
    DASH,
    '''</head>''',
    '''<style id="freshness-ui">
.freshness-panel{
  margin:0 0 12px;
  background:linear-gradient(145deg,var(--card),var(--card2));
  border:1px solid var(--line);
  border-radius:15px;
  box-shadow:0 8px 24px rgba(0,0,0,.12);
  overflow:hidden;
}
.freshness-head{
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:12px 15px;border-bottom:1px solid var(--line);
}
.freshness-title{font-weight:900;font-size:13px}
.freshness-sub{font-size:11px;color:var(--mut);margin-top:2px}
.freshness-source{
  padding:5px 9px;border:1px solid var(--line);border-radius:999px;
  font-size:11px;font-weight:800;white-space:nowrap;
}
.freshness-source.direct{color:var(--ok);border-color:rgba(34,199,122,.35);background:rgba(34,199,122,.08)}
.freshness-source.worker{color:var(--blue);border-color:rgba(108,140,255,.35);background:rgba(108,140,255,.08)}
.freshness-source.blocked{color:var(--no);border-color:rgba(255,77,95,.4);background:rgba(255,77,95,.08)}
.freshness-events{display:grid;gap:0}
.freshness-row{
  display:grid;grid-template-columns:minmax(150px,1.2fr) auto minmax(150px,1fr);
  gap:10px;align-items:center;padding:9px 15px;border-top:1px solid var(--line);
}
.freshness-row:first-child{border-top:0}
.freshness-name{font-weight:800;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.freshness-state{font-size:11px;font-weight:800;padding:4px 8px;border-radius:999px;background:var(--soft);white-space:nowrap}
.freshness-state.ok{color:var(--ok)}
.freshness-state.warn{color:var(--warn)}
.freshness-state.bad{color:var(--no)}
.freshness-time{text-align:right;font-size:12px;color:var(--mut)}
.freshness-time b{color:var(--text)}
@media(max-width:600px){
  .freshness-head{align-items:flex-start}
  .freshness-row{grid-template-columns:1fr auto;gap:7px}
  .freshness-time{grid-column:1/-1;text-align:left}
}
</style>
</head>''',
    "dashboard freshness CSS",
)

replace_once(
    DASH,
    '''    <div class="radar-metric">
      <span class="radar-metric-label">⚡ Velocity</span>
      <b class="radar-metric-value" id="rcVelocity">—</b>
      <span class="radar-metric-sub">tiket/menit</span>
    </div>
    <div class="radar-metric">
      <span class="radar-metric-label">⏱ Next poll</span>
      <b class="radar-metric-value" id="rcNext">10s</b>
      <span class="radar-metric-sub">auto refresh</span>
    </div>''',
    '''    <div class="radar-metric">
      <span class="radar-metric-label">⚡ Velocity</span>
      <b class="radar-metric-value" id="rcVelocity">—</b>
      <span class="radar-metric-sub">tiket/menit</span>
    </div>
    <div class="radar-metric">
      <span class="radar-metric-label">📡 Source</span>
      <b class="radar-metric-value" id="rcSource">—</b>
      <span class="radar-metric-sub" id="rcSourceSub">—</span>
    </div>
    <div class="radar-metric">
      <span class="radar-metric-label">⏱ Next update</span>
      <b class="radar-metric-value" id="rcNext">—</b>
      <span class="radar-metric-sub" id="rcNextSub">—</span>
    </div>''',
    "dashboard source and next metric",
)

replace_once(
    DASH,
    '''  </section>

  <section class="radar-hot r12-visibility-block"''',
    '''  </section>

  <section class="freshness-panel" id="freshnessPanel" aria-label="Data freshness">
    <div class="freshness-head">
      <div>
        <div class="freshness-title">📡 Data Freshness</div>
        <div class="freshness-sub">Kapan data tiket terakhir diterima dan perkiraan pembaruan berikutnya.</div>
      </div>
      <span class="freshness-source worker" id="freshnessSource">—</span>
    </div>
    <div class="freshness-events" id="freshnessEvents"></div>
  </section>

  <section class="radar-hot r12-visibility-block"''',
    "dashboard freshness panel",
)

old_command = '''  function renderCommand() {
    if (!rc("radarCommand")) return;
    const rows = radarRows();
    const now = data?.now || Math.floor(Date.now()/1000);
    const currentEvent = data?.events?.[tab];
    const stale = currentEvent?.updated ? now-currentEvent.updated > (data.stale_after || 90) : true;
    const ten = feed.filter(f => f.at && (Date.now()-f.at*1000) <= 600000);
    const velocity = rows.reduce((a,l)=>a+Number(l.rate||0),0);
    const hot = radarHotData()[0];

    rc("rcStatus").textContent = stale ? "STALE" : "LIVE";
    rc("rcStatus").style.color = stale ? "var(--warn)" : "var(--ok)";
    rc("rcUpdated").textContent = currentEvent?.updated ? radarAge(currentEvent.updated*1000) : "menunggu data";
    rc("rcRestock").textContent = String(ten.length);
    rc("rcHot").textContent = hot ? hot.member : "—";
    rc("rcHotSub").textContent = hot ? (hot.quota.toLocaleString("id-ID")+" tiket · "+hot.available+" jalur") : "menunggu data";
    rc("rcVelocity").textContent = velocity ? velocity.toFixed(1) : "0";
    const interval = Number(data?.poller?.interval || 10);
    const elapsed = Math.floor((Date.now()-lastLoadMark)/1000);
    rc("rcNext").textContent = Math.max(0,interval-(elapsed%interval))+"s";
  }'''
new_command = '''  function renderCommand() {
    if (!rc("radarCommand")) return;

    const rows = radarRows();
    const now = data?.now || Math.floor(Date.now()/1000);
    const currentEvent = data?.events?.[tab];
    const staleAfter = Number(data?.stale_after || 150);
    const age = currentEvent?.updated ? Math.max(0, now-currentEvent.updated) : Infinity;
    const stale = !currentEvent?.updated || age > staleAfter;
    const ten = feed.filter(f => f.at && (Date.now()-f.at*1000) <= 600000);
    const velocity = rows.reduce((a,l)=>a+Number(l.rate||0),0);
    const hot = radarHotData()[0];

    const poller = data?.poller || {};
    const direct = poller.mode === "direct";
    const blocked = !!poller.blocked;
    const sourceText = direct ? "Direct Poller" : "Browser";
    const sourceSub = direct
      ? (blocked ? "Cloudflare / backoff" : "jkt48.com API")
      : "Chrome Extension / Worker";

    rc("rcStatus").textContent = stale ? "STALE" : (blocked ? "BLOCKED" : "LIVE");
    rc("rcStatus").style.color =
      stale ? "var(--warn)" : (blocked ? "var(--no)" : "var(--ok)");

    rc("rcUpdated").textContent = currentEvent?.updated
      ? radarAge(currentEvent.updated*1000)
      : "menunggu data";

    rc("rcRestock").textContent = String(ten.length);
    rc("rcHot").textContent = hot ? hot.member : "—";
    rc("rcHotSub").textContent = hot
      ? (hot.quota.toLocaleString("id-ID")+" tiket · "+hot.available+" jalur")
      : "menunggu data";

    rc("rcVelocity").textContent = velocity ? velocity.toFixed(1) : "0";

    if (rc("rcSource")) rc("rcSource").textContent = sourceText;
    if (rc("rcSourceSub")) rc("rcSourceSub").textContent = sourceSub;

    const nextAt = Number(currentEvent?.next_at || poller.next_at || 0);
    const left = nextAt ? Math.max(0, Math.ceil(nextAt - now)) : null;

    if (rc("rcNext")) {
      rc("rcNext").textContent = left != null
        ? ((blocked ? "~" : "") + left + "s")
        : "—";
    }

    if (rc("rcNextSub")) {
      if (blocked) {
        const b = Number(poller.backoff || 0);
        rc("rcNextSub").textContent = b ? "backoff " + b + "s" : "menunggu retry";
      } else if (direct) {
        rc("rcNextSub").textContent = "poller berikutnya";
      } else {
        rc("rcNextSub").textContent = left != null
          ? "perkiraan extension"
          : "menunggu laporan";
      }
    }
  }

  function renderFreshness() {
    const box = rc("freshnessEvents");
    const source = rc("freshnessSource");
    if (!box || !data?.events) return;

    const now = data?.now || Math.floor(Date.now()/1000);
    const staleAfter = Number(data?.stale_after || 150);
    const poller = data?.poller || {};
    const direct = poller.mode === "direct";
    const blocked = !!poller.blocked;

    if (source) {
      source.textContent = blocked
        ? "🔴 CLOUDFLARE / BACKOFF"
        : (direct ? "🟢 DIRECT POLLER" : "🔵 BROWSER EXTENSION");
      source.className = "freshness-source " +
        (blocked ? "blocked" : (direct ? "direct" : "worker"));
    }

    box.textContent = "";

    for (const [code, ev] of Object.entries(data.events)) {
      const age = ev.updated ? Math.max(0, now - ev.updated) : Infinity;

      let state = "bad";
      let stateText = "BELUM ADA DATA";

      if (Number.isFinite(age)) {
        if (age <= staleAfter) {
          state = "ok";
          stateText = "FRESH";
        } else if (age <= staleAfter * 2) {
          state = "warn";
          stateText = "LAMBAT";
        } else {
          state = "bad";
          stateText = "STALE";
        }
      }

      if (blocked && direct) {
        stateText = state === "ok" ? "FRESH · POLLER BLOCKED" : "CLOUDFLARE";
      }

      const row = el("div", "freshness-row");
      const name = el("div", "freshness-name", ev.name);
      const badge = el("span", "freshness-state " + state, stateText);
      const time = el("div", "freshness-time");

      if (ev.updated) {
        const nextAt = Number(ev.next_at || 0);
        const left = nextAt ? Math.max(0, Math.ceil(nextAt - now)) : null;
        const last = new Date(ev.updated * 1000).toLocaleTimeString("id-ID", {
          hour: "2-digit", minute: "2-digit", second: "2-digit"
        });

        time.append(
          el("b", "", last),
          document.createTextNode(" · " + radarAge(ev.updated * 1000))
        );

        if (left != null) {
          time.append(document.createTextNode(" · berikutnya ~" + left + "s"));
        }
      } else {
        time.textContent = "belum pernah menerima data";
      }

      row.append(name, badge, time);
      box.append(row);
    }
  }'''
replace_once(DASH, old_command, new_command, "dashboard command center logic")

replace_once(
    DASH,
    '''  function renderAllEnhancements() {
    renderCommand();
    renderHot();
  }''',
    '''  function renderAllEnhancements() {
    renderCommand();
    renderFreshness();
    renderHot();
  }''',
    "dashboard render enhancements",
)

replace_once(
    DASH,
    '''  setInterval(() => {
    renderCommand();
    if (!document.hidden && data) renderHot();
  }, 1000);''',
    '''  setInterval(() => {
    renderCommand();
    renderFreshness();
    if (!document.hidden && data) renderHot();
  }, 1000);''',
    "dashboard one-second freshness refresh",
)

print("Patch berhasil diterapkan.")
print("Backup dibuat sebagai *.freshness.bak")
print("Restart/redeploy server setelah patch.")
