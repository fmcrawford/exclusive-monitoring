# JKT48 Ticket Radar — Data Freshness Patch

Patch ini menambahkan:
- waktu data terakhir diterima per event
- sumber data: Direct Poller atau Browser Extension
- perkiraan waktu update berikutnya
- telemetry Cloudflare/backoff
- panel Data Freshness di dashboard
- countdown diperbarui setiap 1 detik

## Jalankan

Taruh `apply_freshness_patch.py` di root repository, lalu:

```bash
python apply_freshness_patch.py
```

Setelah itu restart/deploy ulang server.

## Kondisi kamu sekarang

Karena direct poller sedang terkena Cloudflare 403, mode browser extension dapat dipakai:

```env
POLL_ENABLED=0
WORKER_INTERVAL=30
```

Dalam mode ini dashboard menampilkan waktu laporan terakhir dan **perkiraan** update berikutnya berdasarkan interval extension 30 detik.
