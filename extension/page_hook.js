(() => {
  "use strict";

  if (window.__JKT48_RADAR_4EVENT_HOOK__) return;
  window.__JKT48_RADAR_4EVENT_HOOK__ = true;

  const TAG = "JKT48_HOOK";
  const EVENT_CODES = ["EX5B99", "EX24AE", "EXD1A1", "EXA6F1"];
  const REQUEST_GAP_MS = 7500;

  const originalFetch = window.fetch.bind(window);

  function apiUrl(code) {
    return `/api/v1/exclusives/${encodeURIComponent(code)}/bonus?lang=id`;
  }

  function codeFromUrl(url) {
    try {
      const absolute = new URL(String(url || ""), location.href);
      const m = absolute.pathname.match(/\/api\/v1\/exclusives\/(EX[0-9A-Z]+)\/bonus/i);
      return m ? m[1].toUpperCase() : null;
    } catch {
      return null;
    }
  }

  function looksLikeTicketData(json) {
    return json && Array.isArray(json.data);
  }

  function publish(code, json, url) {
    if (!EVENT_CODES.includes(code)) return;
    window.postMessage(
      { source: TAG, type: "DATA", code, url, json },
      location.origin
    );
  }

  async function fetchEvent(code) {
    const url = apiUrl(code);

    try {
      const response = await originalFetch(url, {
        method: "GET",
        credentials: "include",
        cache: "no-store",
        headers: {
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
        }
      });

      const text = await response.text();

      if (!response.ok) {
        window.postMessage(
          { source: TAG, type: "ERROR", code, error: `HTTP ${response.status}` },
          location.origin
        );
        return;
      }

      let json;
      try {
        json = JSON.parse(text);
      } catch {
        window.postMessage(
          { source: TAG, type: "ERROR", code, error: "Respons bukan JSON" },
          location.origin
        );
        return;
      }

      if (!looksLikeTicketData(json)) {
        window.postMessage(
          { source: TAG, type: "ERROR", code, error: "Struktur data API tidak dikenali" },
          location.origin
        );
        return;
      }

      publish(code, json, url);
    } catch (error) {
      window.postMessage(
        {
          source: TAG,
          type: "ERROR",
          code,
          error: String(error?.message || error)
        },
        location.origin
      );
    }
  }

  window.fetch = function(input, init) {
    const promise = originalFetch(input, init);

    promise.then(response => {
      try {
        const url = typeof input === "string" ? input : input?.url || String(input);
        const code = codeFromUrl(url);
        if (!code || !EVENT_CODES.includes(code)) return;

        response.clone().json()
          .then(json => {
            if (looksLikeTicketData(json)) publish(code, json, url);
          })
          .catch(() => {});
      } catch {}
    }).catch(() => {});

    return promise;
  };

  let index = 0;

  function pollNext() {
    const code = EVENT_CODES[index % EVENT_CODES.length];
    index += 1;
    fetchEvent(code);
  }

  setTimeout(pollNext, 1200);
  setInterval(pollNext, REQUEST_GAP_MS);

  window.addEventListener("message", event => {
    if (event.source !== window || event.origin !== location.origin) return;
    if (event.data?.source !== "JKT48_CONTENT") return;

    if (event.data.type === "REFETCH_ALL") {
      EVENT_CODES.forEach((code, i) => {
        setTimeout(() => fetchEvent(code), i * 1200);
      });
    }
  });

  console.log("[JKT48 Radar] 4-event browser poller aktif.");
})();
