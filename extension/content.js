(() => {
  "use strict";

  if (window.__JKT48_RADAR_4EVENT_CONTENT__) return;
  window.__JKT48_RADAR_4EVENT_CONTENT__ = true;

  const ALLOWED_CODES = new Set([
    "EX5B99",
    "EX24AE",
    "EXD1A1",
    "EXA6F1"
  ]);

  const STORAGE_PREFIX = "jkt48-ticket-radar-4event:";
  const lastSentAt = new Map();
  const MIN_SEND_GAP_MS = 2500;

  const clean = value =>
    String(value ?? "").replace(/\s+/g, " ").trim();

  function quotaValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  function normalizePayload(json) {
    const lanes = [];
    const data = json?.data;

    if (!Array.isArray(data)) return lanes;

    for (const session of data) {
      if (!session || typeof session !== "object") continue;

      const members = Array.isArray(session.session_members)
        ? session.session_members
        : [];

      for (const member of members) {
        if (!member || typeof member !== "object") continue;

        const sdc = clean(member.session_detail_code);
        const quota = quotaValue(member.available_quota);

        if (!sdc || quota === null) continue;

        lanes.push({
          label: clean(member.label) || "-",
          price: member.price,
          member_name: clean(member.member_name) || "Tidak diketahui",
          session_detail_code: sdc,
          available_quota: quota,
          session_label: clean(session.label) || "-",
          session_date: clean(session.date) || "-",
          session_start_time: clean(session.start_time),
          session_end_time: clean(session.end_time),
          source: "browser-api"
        });
      }
    }

    return lanes;
  }

  function recordKey(record) {
    return [
      record.session_detail_code,
      record.member_name,
      record.label
    ].join("|").toLowerCase();
  }

  function compareRecords(previous, current) {
    const oldMap = new Map(
      (Array.isArray(previous) ? previous : []).map(x => [recordKey(x), x])
    );
    const changes = [];

    for (const now of current) {
      const old = oldMap.get(recordKey(now));

      if (!old) {
        changes.push(
          `NEW ${now.member_name} ${now.label}: ${now.available_quota}`
        );
        continue;
      }

      const before = quotaValue(old.available_quota);
      const after = quotaValue(now.available_quota);

      if (before !== after) {
        changes.push(
          `${now.member_name} ${now.label}: ${before ?? "?"} -> ${after ?? "?"}`
        );
      }
    }

    return changes.slice(0, 200);
  }

  async function sendEventReport(code, json) {
    if (!ALLOWED_CODES.has(code)) return;

    const now = Date.now();
    if (now - (lastSentAt.get(code) || 0) < MIN_SEND_GAP_MS) return;
    lastSentAt.set(code, now);

    const lanes = normalizePayload(json);
    const storageKey = STORAGE_PREFIX + code;

    let previous = [];
    try {
      const stored = await chrome.storage.local.get(storageKey);
      previous = stored?.[storageKey]?.lanes || [];
    } catch {}

    const changes = compareRecords(previous, lanes);

    const payload = {
      code,
      title: "JKT48 Ticket Radar",
      scannedAt: new Date().toLocaleString("id-ID", {
        timeZone: "Asia/Jakarta"
      }),
      laneCount: lanes.length,
      lanes,
      changes,
      source: "browser-api"
    };

    chrome.runtime.sendMessage(
      { type: "JKT48_FULL_REPORT", payload },
      response => {
        if (chrome.runtime.lastError) {
          console.error(
            `[JKT48 Radar] ${code} background error:`,
            chrome.runtime.lastError.message
          );
          return;
        }

        if (!response?.ok) {
          console.error(
            `[JKT48 Radar] ${code} gagal dikirim:`,
            response
          );
          return;
        }

        console.log(
          `[JKT48 Radar] ${code} terkirim: ${lanes.length} lane`
        );
      }
    );

    if (lanes.length > 0) {
      try {
        await chrome.storage.local.set({
          [storageKey]: {
            lanes,
            scannedAt: Date.now()
          }
        });
      } catch {}
    }
  }

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    if (event.data?.source !== "JKT48_HOOK") return;

    const code = String(event.data.code || "").trim().toUpperCase();
    if (!ALLOWED_CODES.has(code)) return;

    if (event.data.type === "ERROR") {
      console.warn(
        `[JKT48 Radar] ${code} API error:`,
        event.data.error
      );
      return;
    }

    if (event.data.type !== "DATA") return;

    sendEventReport(code, event.data.json).catch(error => {
      console.error(`[JKT48 Radar] ${code} report error:`, error);
    });
  });

  setTimeout(() => {
    window.postMessage(
      { source: "JKT48_CONTENT", type: "REFETCH_ALL" },
      location.origin
    );
  }, 2500);

  console.log("[JKT48 Radar] bridge 4 event aktif.");
})();
