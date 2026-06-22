# --- Secret Manager ---
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "agri-saathi-gemini-api-key"
  project   = var.project_id
  replication { auto {} }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "agri-saathi-jwt-secret"
  project   = var.project_id
  replication { auto {} }
}
