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

        dynamic "env" {
          for_each = var.secret_environment_variables
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }

        dynamic "volume_mounts" {
          for_each = length(var.cloud_sql_instances) > 0 ? [1] : []
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }
      }

      dynamic "volumes" {
        for_each = length(var.cloud_sql_instances) > 0 ? [1] : []
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = var.cloud_sql_instances
          }
        }
      }
    }
  }

  depends_on = [module.docker_image]
}
