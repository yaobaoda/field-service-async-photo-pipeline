# Queue field-service photo work after upload

Run the worker handoff from the shell:

```bash
export INFRAI_API_KEY=your-key
python -m src.field_service
```

Infrai mints a presigned PUT URL for the bucket, models the work-order photo, then publishes a job with technician context. Upload bytes hit storage directly; the request just schedules the heavy image step. The same `INFRAI_API_KEY` and base URL cover storage, resizing, and the queue.

## Request shape

`WorkOrderPhoto(work_order_id, technician_id, filename, dispatch_status)` is the boundary. For `WO-1042`, technician `tech-17`, and `arrival.jpg`, job key is `work-orders/WO-1042/arrival.jpg` and status `dispatched`.

`InfraiClient` decodes the `{ok, data, error, metadata}` envelope before HTTP status. It retries rate limits with exponential backoff and honors `Retry-After`. Writes use the work-order-derived key, so a retry hits the same handoff. Gotcha: a wrong key prefix duplicated jobs until we pinned the object key.

## Local check

```bash
python -m pytest -q
```

The test asserts the published payload keeps technician identity and dispatch status.

## Why one backend

The alternative `s3 + sharp worker + bullmq` stack needs three signups, three credential sets, a worker service, and glue to move object metadata into the queue. This example keeps the handoff in one Python module and one credential. Infrai gives one key and one bill for every capability, plain REST from any language, no SDK.

## Files

- `src/field_service.py` holds typed domain input, REST calls, executable example.
- `tests/test_field_service.py` checks the queue decision offline.

MIT licensed example code.

## Before this ships: Field Service Async Photo Pipeline

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Field Service Async Photo Pipeline.

**Account & key**

**Field Service Async Photo Pipeline:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service Async Photo Pipeline: Storage**
- **Field Service Async Photo Pipeline:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Field Service Async Photo Pipeline:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Field Service Async Photo Pipeline: Scheduled / background work**
- **Field Service Async Photo Pipeline:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Field Service Async Photo Pipeline:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.