output "api_url" {
  description = "API Gateway URL"
  value       = google_cloud_run_v2_service.api_gateway.uri
}

output "weather_mcp_url" {
  description = "Weather MCP Server URL"
  value       = google_cloud_run_v2_service.weather_mcp.uri
}

output "mandi_mcp_url" {
  description = "Mandi MCP Server URL"
  value       = google_cloud_run_v2_service.mandi_mcp.uri
}

output "schemes_mcp_url" {
  description = "Schemes MCP Server URL"
  value       = google_cloud_run_v2_service.schemes_mcp.uri
}
