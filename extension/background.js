"use strict";

const ALLOWED_CODES = new Set([
  "EX5B99",
  "EX24AE",
  "EXD1A1",
  "EXA6F1"
]);

async function getNotifierConfig() {
  const cfg = await chrome.storage.local.get([
    "notifierUrl",
    "notifySecret"
  ]);

  const notifierUrl = String(cfg.notifierUrl || "").trim();
  const notifySecret = String(cfg.notifySecret || "").trim();

  if (!notifierUrl || !notifySecret) {
    throw new Error(
      "Notifier belum dikonfigurasi. Buka Manage extension > Extension options."
    );
  }

  let parsed;
  try {
    parsed = new URL(notifierUrl);
  } catch {
    throw new Error("Notifier URL tidak valid.");
  }

  if (parsed.protocol !== "https:") {
    throw new Error("Notifier URL harus menggunakan HTTPS.");
  }

  const originPattern = parsed.origin + "/*";
  const permitted = await chrome.permissions.contains({
    origins: [originPattern]
  });

  if (!permitted) {
    throw new Error(
      "Izin host notifier belum diberikan. Buka Extension options dan simpan ulang konfigurasi."
    );
  }

  return { notifierUrl, notifySecret };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "JKT48_FULL_REPORT") return false;

  const senderUrl = sender.tab?.url || "";
  const payload = message.payload || {};
  const code = String(payload.code || "").trim().toUpperCase();

  if (
    !senderUrl.startsWith("https://jkt48.com/purchase/exclusive") ||
    !ALLOWED_CODES.has(code)
  ) {
    sendResponse({
      ok: false,
      error: `Halaman atau kode event tidak diizinkan: ${code || "-"}`
    });
    return false;
  }

  (async () => {
    try {
      const { notifierUrl, notifySecret } = await getNotifierConfig();

      const response = await fetch(notifierUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Notify-Secret": notifySecret
        },
        body: JSON.stringify({
          ...payload,
          code,
          pageUrl: senderUrl
        })
      });

      const result = await response.json().catch(() => ({
        error: "Server mengembalikan respons yang bukan JSON."
      }));

      sendResponse({
        ok: response.ok && result.ok === true,
        status: response.status,
        result
      });
    } catch (error) {
      sendResponse({
        ok: false,
        error: String(error?.message || error)
      });
    }
  })();

  return true;
});
