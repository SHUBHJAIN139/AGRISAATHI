# --- Service Accounts ---
resource "google_service_account" "api_sa" {
  account_id   = "agri-saathi-api"
  display_name = "AgriSaathi API Service Account"
  project      = var.project_id
}

# Firestore access
resource "google_project_iam_member" "api_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Secret Manager access
resource "google_project_iam_member" "api_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Vertex AI access (for SchemeGuide RAG in production)
resource "google_project_iam_member" "api_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}
