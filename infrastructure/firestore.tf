resource "google_firestore_database" "database" {
  count = var.manage_firestore_database ? 1 : 0

  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
}

resource "google_firestore_field" "sns_promotions_status" {
  project    = var.project_id
  database   = "(default)"
  collection = "sns_promotions"
  field      = "status"

  index_config {
    indexes {
      order       = "ASCENDING"
      query_scope = "COLLECTION_GROUP"
    }
    indexes {
      order       = "DESCENDING"
      query_scope = "COLLECTION_GROUP"
    }
  }
}


