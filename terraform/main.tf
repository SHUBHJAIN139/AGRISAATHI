# =============================================================================
# AgriSaathi — Terraform Configuration
# =============================================================================
# Provisions: Cloud Run (API + 3 MCP servers), Firestore, Secret Manager, IAM
# Usage: terraform init && terraform plan && terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Cloud Run: API Gateway ---
resource "google_cloud_run_v2_service" "api_gateway" {
  name     = "agri-saathi-api"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/agri-saathi/api:latest"

      ports { container_port = 8080 }

      env { name = "MOCK_LLM";          value = "false" }
      env { name = "SESSION_BACKEND";   value = "firestore" }
      env { name = "MCP_TRANSPORT";     value = "sse" }
      env { name = "WEATHER_MCP_URL";   value = google_cloud_run_v2_service.weather_mcp.uri }
      env { name = "MANDI_MCP_URL";     value = google_cloud_run_v2_service.mandi_mcp.uri }
      env { name = "SCHEMES_MCP_URL";   value = google_cloud_run_v2_service.schemes_mcp.uri }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    service_account = google_service_account.api_sa.email
  }
}

# --- Cloud Run: Weather MCP Server ---
resource "google_cloud_run_v2_service" "weather_mcp" {
  name     = "agri-saathi-weather-mcp"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/agri-saathi/weather-mcp:latest"
      ports { container_port = 8081 }
      env { name = "MCP_TRANSPORT"; value = "sse" }
      env { name = "MCP_PORT";      value = "8081" }
      resources { limits = { cpu = "1"; memory = "512Mi" } }
    }
    scaling { min_instance_count = 0; max_instance_count = 5 }
  }
}

# --- Cloud Run: Mandi MCP Server ---
resource "google_cloud_run_v2_service" "mandi_mcp" {
  name     = "agri-saathi-mandi-mcp"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/agri-saathi/mandi-mcp:latest"
      ports { container_port = 8082 }
      env { name = "MCP_TRANSPORT"; value = "sse" }
      env { name = "MCP_PORT";      value = "8082" }
      resources { limits = { cpu = "1"; memory = "512Mi" } }
    }
    scaling { min_instance_count = 0; max_instance_count = 5 }
  }
}

# --- Cloud Run: Schemes MCP Server ---
resource "google_cloud_run_v2_service" "schemes_mcp" {
  name     = "agri-saathi-schemes-mcp"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/agri-saathi/schemes-mcp:latest"
      ports { container_port = 8083 }
      env { name = "MCP_TRANSPORT"; value = "sse" }
      env { name = "MCP_PORT";      value = "8083" }
      resources { limits = { cpu = "1"; memory = "512Mi" } }
    }
    scaling { min_instance_count = 0; max_instance_count = 5 }
  }
}

# Allow unauthenticated access to API gateway
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api_gateway.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
