from src.field_service import WorkOrderPhoto, queue_photo_processing


class FakeClient:
    def __init__(self):
        self.calls = []

    def create_bucket(self, name):
        self.calls.append(("bucket", name))

    def presign_put(self, bucket, key):
        self.calls.append(("presign", bucket, key))
        return {"url": "https://upload.example/signed"}

    def publish(self, payload):
        self.calls.append(("publish", payload))
        return {"message_id": "m-1"}


def test_photo_upload_is_published_with_work_order_context():
    client = FakeClient()
    result = queue_photo_processing(WorkOrderPhoto("WO-9", "tech-2", "front.jpg"), client)
    assert result["object_key"] == "work-orders/WO-9/front.jpg"
    assert client.calls[2][1]["dispatch_status"] == "dispatched"
    assert client.calls[2][1]["technician_id"] == "tech-2"
