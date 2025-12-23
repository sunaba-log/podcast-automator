locals {
  repository_name     = lower("${var.system}-${var.environment}")
  repository_url      = "${var.region}-docker.pkg.dev/${var.project_id}/${local.repository_name}"
  docker_image_latest = "${local.repository_url}/${var.image_name}:latest"
  docker_image        = "${local.repository_url}/${var.image_name}:${md5(data.external.docker_image_digest.result.digest)}"
}
