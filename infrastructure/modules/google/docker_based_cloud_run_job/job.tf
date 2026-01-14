resource "google_cloud_run_v2_job" "job" {
  name                = var.job_name
  location            = var.region
  deletion_protection = var.deletion_protection

  template {
    template {
      service_account = var.service_account_email
      timeout         = var.timeout

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
  }

  depends_on = [module.docker_image]
}
