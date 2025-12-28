import importlib.util
import io
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ID = "taka-test-481815"  # ※それそれのproject_idを確認してください。
SECRET_ID = "sunabalog-r2"  # ※本記事では2で作成した'test-secret')
VERSION = "latest"  # ※私が作成した場合はデフォルトで`1`になってました。`latest`でも取得できました。
ENDPOINT_URL = "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com"
BUCKET_NAME = "podcast"


def _load_storage_module():
    # Load the storage module directly from the services directory to avoid
    # package import issues with the directory name.
    base = Path(__file__).resolve().parents[1]
    storage_path = base / "services" / "storage.py"
    spec = importlib.util.spec_from_file_location("storage", storage_path)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    return storage


def test_download_file(monkeypatch):
    storage = _load_storage_module()

    class FakeClient:
        def __init__(self):
            self.get_object = MagicMock(return_value={"Body": io.BytesIO(b"file-bytes")})

    fake = FakeClient()

    class FakeBotoModule:
        @staticmethod
        def client(*args, **kwargs):
            return fake

    monkeypatch.setattr(storage, "boto3", FakeBotoModule)

    r2 = storage.R2Client(PROJECT_ID, SECRET_ID, ENDPOINT_URL, "bucket")
    data = r2.download_file("remote/key")

    assert data == b"file-bytes"
    fake.get_object.assert_called_once_with(Bucket="bucket", Key="remote/key")


def test_upload_file(monkeypatch):
    storage = _load_storage_module()

    class FakeClient:
        def __init__(self):
            self.upload_fileobj = MagicMock()

    fake = FakeClient()

    class FakeBotoModule:
        @staticmethod
        def client(*args, **kwargs):
            return fake

    monkeypatch.setattr(storage, "boto3", FakeBotoModule)

    r2 = storage.R2Client(PROJECT_ID, SECRET_ID, ENDPOINT_URL, "bucket")
    content = b"hello"
    url = r2.upload_file(content, "remote/key", content_type="text/plain", public=True)

    assert fake.upload_fileobj.call_count == 1
    call_args = fake.upload_fileobj.call_args[0]
    fileobj = call_args[0]
    assert fileobj.read() == content
    assert call_args[1] == "bucket"
    assert call_args[2] == "remote/key"
    assert url == f"{ENDPOINT_URL}/bucket/remote/key"


def test_upload_json_calls_upload_file(monkeypatch):
    storage = _load_storage_module()

    recorded = {}

    def fake_upload(self, file_content, remote_key, content_type=None, public=True):
        recorded["file_content"] = file_content
        recorded["remote_key"] = remote_key
        recorded["content_type"] = content_type
        recorded["public"] = public
        return "http://example.com/json"

    monkeypatch.setattr(storage.R2Client, "upload_file", fake_upload)

    r2 = storage.R2Client(PROJECT_ID, SECRET_ID, ENDPOINT_URL, "bucket")
    url = r2.upload_json({"a": 1}, "data.json", public=False)

    assert url == "http://example.com/json"
    # upload_json writes a temp file and passes its path to upload_file in current implementation
    assert isinstance(recorded["file_content"], str)
    assert recorded["remote_key"] == "data.json"
    assert recorded["content_type"] == "application/json"
    assert recorded["public"] is False


def test_generate_public_url():
    storage = _load_storage_module()
    r2 = storage.R2Client(PROJECT_ID, SECRET_ID, "https://endpoint", "bucket")
    assert r2.generate_public_url("key") == "https://endpoint/bucket/key"
    assert (
        r2.generate_public_url("key", custom_domain="https://cdn.example.com")
        == "https://cdn.example.com/key"
    )
