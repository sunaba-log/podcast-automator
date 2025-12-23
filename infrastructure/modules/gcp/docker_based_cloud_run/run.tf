resource "google_cloud_run_v2_service" "service" {
  name     = var.service_name
  location = var.region

  template {
    service_account = var.service_account_email
    timeout         = "${var.timeout_seconds}s"

    annotations = { "image-digest" = module.docker_image.docker_image_digest }

    scaling {
      max_instance_count = var.max_instance_count
    }

    containers {
      image = module.docker_image.docker_image_name

      resources {
        limits = {
          memory = var.memory
          cpu    = var.cpu
        }
      }

      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  depends_on = [module.docker_image]
}
