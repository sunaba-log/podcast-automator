import io
from unittest.mock import MagicMock

from services import R2Client

PROJECT_ID = "taka-test-481815"  # ※それそれのproject_idを確認してください。
SECRET_ID = "sunabalog-r2"  # ※本記事では2で作成した'test-secret')
VERSION = "latest"  # ※私が作成した場合はデフォルトで`1`になってました。`latest`でも取得できました。
ENDPOINT_URL = "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com"
BUCKET_NAME = "podcast"


def test_download_file(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.get_object = MagicMock(return_value={"Body": io.BytesIO(b"file-bytes")})

    fake = FakeClient()

    r2 = R2Client(PROJECT_ID, SECRET_ID, ENDPOINT_URL, "bucket")
    data = r2.download_file("remote/key")

    assert data == b"file-bytes"
    fake.get_object.assert_called_once_with(Bucket="bucket", Key="remote/key")


def test_upload_file(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.upload_fileobj = MagicMock()

    fake = FakeClient()

    r2 = R2Client(PROJECT_ID, SECRET_ID, ENDPOINT_URL, "bucket")
    content = b"hello"
    url = r2.upload_file(content, "remote/key", content_type="text/plain", public=True)

    assert fake.upload_fileobj.call_count == 1
    call_args = fake.upload_fileobj.call_args[0]
    fileobj = call_args[0]
    assert fileobj.read() == content
    assert call_args[1] == "bucket"
    assert call_args[2] == "remote/key"
    assert url == f"{ENDPOINT_URL}/bucket/remote/key"


def test_generate_public_url():
    r2 = R2Client(PROJECT_ID, SECRET_ID, "https://endpoint", "bucket")
    assert r2.generate_public_url("key") == "https://endpoint/bucket/key"
    assert r2.generate_public_url("key", custom_domain="https://cdn.example.com") == "https://cdn.example.com/key"
    assert r2.generate_public_url("key") == "https://endpoint/bucket/key"
    assert r2.generate_public_url("key", custom_domain="https://cdn.example.com") == "https://cdn.example.com/key"
