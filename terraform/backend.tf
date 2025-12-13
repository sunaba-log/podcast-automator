terraform {
  backend "gcs" {
    # 初回は以下をコメントアウトしており、terraform init -backend-config を使用
    # または、スクリプトから以下のパラメタを渡す
    # bucket  = "your-terraform-state-bucket"
    # prefix  = "podcast-automator"
  }
}

# 代替案：環境変数 TF_BACKEND_BUCKET_NAME でバケット名を指定
# または、init時に -backend-config="bucket=your-bucket" を指定
