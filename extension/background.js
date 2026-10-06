"use strict";

const NOTIFIER_URL = "https://jkt48-deplexo-bot-production.up.railway.app//notify";
const NOTIFY_SECRET = "mzPgq6wNe6ZwzXT8IiS1JuoYAhLJlKaTEb1dd-QUuMI";

const ALLOWED_CODES = new Set([
  "EX5B99",
  "EX24AE",
  "EXD1A1",
  "EXA6F1"
]);

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

  fetch(NOTIFIER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Notify-Secret": NOTIFY_SECRET
    },
    body: JSON.stringify({
      ...payload,
      code,
      pageUrl: senderUrl
    })
  })
    .then(async response => {
      const result = await response.json().catch(() => ({
        error: "Server mengembalikan respons yang bukan JSON."
      }));

      sendResponse({
        ok: response.ok && result.ok === true,
        status: response.status,
        result
      });
    })
    .catch(error => {
      sendResponse({
        ok: false,
        error: `Tidak dapat menghubungi notifier: ${error.message}`
      });
    });

  return true;
});
