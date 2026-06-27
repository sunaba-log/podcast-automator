resource "google_firestore_database" "database" {
  count = var.manage_firestore_database ? 1 : 0

  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
}

resource "google_firestore_index" "sns_promotions_status" {
  project     = var.project_id
  database    = "(default)"
  collection  = "sns_promotions"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
}

