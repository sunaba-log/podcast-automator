import io
from unittest.mock import MagicMock

import boto3

from infrastructure.storage import R2Client

PROJECT_ID = "sunabalog-dev"  # ※それそれのproject_idを確認してください。
SECRET_ID = "sunabalog-r2"  # ※本記事では2で作成した'test-secret')
VERSION = "latest"  # ※私が作成した場合はデフォルトで`1`になってました。`latest`でも取得できました。
ENDPOINT_URL = "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com"
BUCKET_NAME = "podcast"


def _client_factory(client):
    def _client(*_args, **_kwargs):
        return client

    return _client


def test_download_file(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.get_object = MagicMock(return_value={"Body": io.BytesIO(b"file-bytes")})

    fake = FakeClient()
    monkeypatch.setattr(boto3, "client", _client_factory(fake))

    r2 = R2Client(
        PROJECT_ID,
        ENDPOINT_URL,
        "bucket",
        access_key="test-access-key",
        secret_key="test-secret-key",
    )
    data = r2.download_file("remote/key")

    assert data == b"file-bytes"
    fake.get_object.assert_called_once_with(Bucket="bucket", Key="remote/key")


def test_upload_file(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.upload_fileobj = MagicMock()

    fake = FakeClient()
    monkeypatch.setattr(boto3, "client", _client_factory(fake))

    r2 = R2Client(
        PROJECT_ID,
        ENDPOINT_URL,
        "bucket",
        access_key="test-access-key",
        secret_key="test-secret-key",
    )
    content = b"hello"
    url = r2.upload_file(content, "remote/key", content_type="text/plain", public=True)

    assert fake.upload_fileobj.call_count == 1
    call_args = fake.upload_fileobj.call_args[0]
    fileobj = call_args[0]
    assert fileobj.read() == content
    assert call_args[1] == "bucket"
    assert call_args[2] == "remote/key"
    assert url == f"{ENDPOINT_URL}/bucket/remote/key"


def test_generate_public_url(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(boto3, "client", _client_factory(fake_client))

    r2 = R2Client(
        PROJECT_ID,
        "https://endpoint",
        "bucket",
        access_key="test-access-key",
        secret_key="test-secret-key",
    )
    assert r2.generate_public_url("key") == "https://endpoint/bucket/key"
    assert r2.generate_public_url("key", custom_domain="cdn.example.com") == "https://cdn.example.com/key"
    assert r2.generate_public_url("key") == "https://endpoint/bucket/key"
    assert r2.generate_public_url("key", custom_domain="cdn.example.com") == "https://cdn.example.com/key"
