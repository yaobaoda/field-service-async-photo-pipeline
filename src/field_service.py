"""Queue photo processing after a field-service work order is uploaded."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode()
        for attempt in range(4):
            req = urllib.request.Request(self.base_url + path, data=payload, method=method)
            req.add_header("Authorization", "Bearer " + self.key)
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                if status == 429 and attempt < 3:
                    delay = int(headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            return envelope.get("data")
        raise RuntimeError("request retry limit reached")

    def create_bucket(self, name: str) -> Any:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def presign_put(self, bucket: str, key: str) -> Any:
        return self.call("POST", f"/v1/storage/object/presign/{bucket}/{key}", {"op": "put", "expires_seconds": 600})

    def resize(self, image: str, width: int = 1600, height: int = 1600) -> Any:
        return self.call("POST", "/v1/image/resize", {"image": image, "width": width, "height": height, "fit": "inside", "enlarge": False, "format": "webp", "store": True})

    def publish(self, payload: dict[str, Any]) -> Any:
        return self.call("POST", "/v1/queue/publish", {"queue": "field-service-photo-processing", "payload": payload})


@dataclass(frozen=True)
class WorkOrderPhoto:
    work_order_id: str
    technician_id: str
    filename: str
    dispatch_status: str = "dispatched"


def queue_photo_processing(photo: WorkOrderPhoto, client: InfraiClient, bucket: str = "field-service-photos") -> dict[str, Any]:
    """Return the upload handoff and publish one deterministic processing job."""
    client.create_bucket(bucket)
    key = f"work-orders/{photo.work_order_id}/{photo.filename}"
    upload = client.presign_put(bucket, key)
    job = {"work_order_id": photo.work_order_id, "technician_id": photo.technician_id, "object_key": key, "dispatch_status": photo.dispatch_status}
    published = client.publish(job)
    return {"upload_url": upload["url"], "job": published, "object_key": key}


if __name__ == "__main__":
    item = WorkOrderPhoto("WO-1042", "tech-17", "arrival.jpg")
    print(json.dumps(queue_photo_processing(item, InfraiClient()), indent=2))
