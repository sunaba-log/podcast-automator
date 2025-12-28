# Import the Secret Manager client library.
import json

# https://docs.cloud.google.com/secret-manager/regional-secrets/reference/libraries?hl=ja#client-libraries-install-python
from google.cloud import secretmanager_v1

# Endpoint to call the regional secret manager sever
# api_endpoint = f"secretmanager.{location_id}.rep.googleapis.com"

# Create the Secret Manager client.
client = secretmanager_v1.SecretManagerServiceClient()
PROJECT_ID = "taka-test-481815"  # ※それそれのproject_idを確認してください。
SECRET_ID = "sunabalog-r2"  # ※本記事では2で作成した'test-secret')
VERSION = "latest"  # ※私が作成した場合はデフォルトで`1`になってました。`latest`でも取得できました。

secret_path = client.secret_version_path(PROJECT_ID, SECRET_ID, VERSION)
response = client.access_secret_version(request={"name": secret_path})
secret_value = response.payload.data.decode("UTF-8")

secret_dict = json.loads(secret_value)
access_key_id = secret_dict.get("access_key")
secret_access_key = secret_dict.get("secret_key")
print(access_key_id)
print(secret_value)
