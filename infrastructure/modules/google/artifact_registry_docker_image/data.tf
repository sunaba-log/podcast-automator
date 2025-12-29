data "external" "docker_image_digest" {
  program    = ["bash", "-c", "docker inspect --format='{\"digest\": \"{{.Id}}\"}' ${local.docker_image_latest} | sed 's/sha256://'"]
  depends_on = [null_resource.docker_build]
}
