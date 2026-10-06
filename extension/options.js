"use strict";

const $ = id => document.getElementById(id);
const status = $("status");

function show(text, ok) {
  status.textContent = text;
  status.className = ok ? "ok" : "err";
}

function normalizeEndpoint(raw) {
  const u = new URL(String(raw || "").trim());

  if (u.protocol !== "https:") {
    throw new Error("URL harus menggunakan HTTPS.");
  }

  u.hash = "";
  u.search = "";

  let path = u.pathname.replace(/\/+$/, "");
  if (!path || path === "/") path = "/notify";
  else if (!path.endsWith("/notify")) path += "/notify";

  u.pathname = path;
  return u.toString();
}

async function load() {
  const cfg = await chrome.storage.local.get([
    "notifierUrl",
    "notifySecret"
  ]);

  if (cfg.notifierUrl) $("url").value = cfg.notifierUrl;

  show(
    cfg.notifierUrl && cfg.notifySecret
      ? "Konfigurasi tersimpan. Secret tidak ditampilkan."
      : "Masukkan URL notifier dan secret.",
    !!(cfg.notifierUrl && cfg.notifySecret)
  );
}

$("form").addEventListener("submit", async event => {
  event.preventDefault();

  try {
    const notifierUrl = normalizeEndpoint($("url").value);
    const parsed = new URL(notifierUrl);
    const originPattern = parsed.origin + "/*";

    const granted = await chrome.permissions.request({
      origins: [originPattern]
    });

    if (!granted) {
      throw new Error("Izin akses ke host notifier ditolak.");
    }

    const current = await chrome.storage.local.get(["notifySecret"]);
    const typedSecret = $("secret").value.trim();
    const notifySecret = typedSecret || String(current.notifySecret || "").trim();

    if (!notifySecret) {
      throw new Error("NOTIFY_SECRET belum diisi.");
    }

    await chrome.storage.local.set({
      notifierUrl,
      notifySecret
    });

    $("url").value = notifierUrl;
    $("secret").value = "";

    show(
      "Tersimpan. Izin host aktif. Reload tab JKT48 setelah menutup halaman ini.",
      true
    );
  } catch (error) {
    show(String(error?.message || error), false);
  }
});

load().catch(error => show(String(error?.message || error), false));
