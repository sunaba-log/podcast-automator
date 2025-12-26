resource "null_resource" "docker_build" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<EOF
        set -e
        cd ${var.docker_context_path}
        ${var.docker_build_command}
        if [ -n "${var.docker_build_result_image_name}" ]; then
          docker tag ${var.docker_build_result_image_name} ${local.docker_image_latest}
        fi
    EOF
  }
}

resource "null_resource" "docker_push" {
  triggers = {
    digest = data.external.docker_image_digest.result.digest
  }

  provisioner "local-exec" {
    command = <<EOF
        set -e
        gcloud auth configure-docker ${var.region}-docker.pkg.dev --quiet
        docker tag ${local.docker_image_latest} ${local.docker_image}
        docker push ${local.docker_image}
    EOF
  }

  depends_on = [
    google_artifact_registry_repository.main,
    null_resource.docker_build,
  ]
}
