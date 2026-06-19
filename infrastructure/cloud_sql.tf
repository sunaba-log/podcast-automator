resource "google_sql_database_instance" "podcast" {
  name             = "${var.system}-postgres-${var.environment}"
  database_version = "POSTGRES_17"
  region           = var.region
  project          = var.project_id

  deletion_protection = var.environment == "prod"

  settings {
    edition           = "ENTERPRISE"
    tier              = var.cloud_sql_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.environment == "prod" ? 20 : 10
    disk_autoresize   = true

    backup_configuration {
      enabled                        = var.environment == "prod"
      point_in_time_recovery_enabled = var.environment == "prod"
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "podcast" {
  name     = var.cloud_sql_database_name
  instance = google_sql_database_instance.podcast.name
  project  = var.project_id
}

resource "random_password" "podcast_database" {
  length  = 32
  special = false
}

resource "google_sql_user" "podcast" {
  name     = var.cloud_sql_database_user
  instance = google_sql_database_instance.podcast.name
  password = random_password.podcast_database.result
  project  = var.project_id
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = var.database_url_secret_name
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = format(
    "postgresql://%s:%s@/%s?host=/cloudsql/%s",
    var.cloud_sql_database_user,
    random_password.podcast_database.result,
    var.cloud_sql_database_name,
    google_sql_database_instance.podcast.connection_name,
  )
}

resource "google_secret_manager_secret" "database_password" {
  secret_id = "${var.system}-database-password-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_password" {
  secret      = google_secret_manager_secret.database_password.id
  secret_data = random_password.podcast_database.result
}
