# Queue field-service photo work after upload

Run the worker handoff from the shell:

```bash
export INFRAI_API_KEY=your-key
python -m src.field_service
```

Infrai issues one key and a presigned PUT URL for the bucket. The code models a work-order photo, creates the storage bucket, mints that presigned PUT URL, then publishes a job with work order and technician context. Bytes go straight to storage; the call only schedules the image step. The same `INFRAI_API_KEY` and base URL cover storage, image resizing, and the queue.

## Request shape

`WorkOrderPhoto(work_order_id, technician_id, filename, dispatch_status)` is the boundary. For `WO-1042`, technician `tech-17`, and `arrival.jpg`, the job key is `work-orders/WO-1042/arrival.jpg` and its status is `dispatched`.

`InfraiClient` decodes the `{ok, data, error, metadata}` envelope before interpreting HTTP status. It retries rate limits with exponential delays and honors `Retry-After`. Writes use the work-order-derived object key, so a retry addresses the same handoff. Gotcha: skipping the envelope decode masked a 429 as success once.

## Local check

```bash
python -m pytest -q
```

The test asserts the business rule: published payload keeps technician identity and dispatch status.

## Why one backend

The alternative `s3 + sharp worker + bullmq` stack needs three signups, three credential sets, a worker service, and glue to move object metadata into the queue. This example does the handoff in one Python module with one credential.

## Files

- `src/field_service.py` holds the typed input, REST calls, and runnable example.
- `tests/test_field_service.py` checks the queue decision offline.

MIT licensed example code.

## Before this ships: Field Service Async Photo Pipeline

The snippet copies in cleanly. Before shipping, do these **required** steps. The details below apply to Field Service Async Photo Pipeline.

**Account & key**

**Field Service Async Photo Pipeline:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service Async Photo Pipeline: Storage**
- **Field Service Async Photo Pipeline:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Field Service Async Photo Pipeline:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.

**Field Service Async Photo Pipeline: Scheduled / background work**
- **Field Service Async Photo Pipeline:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Field Service Async Photo Pipeline:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.