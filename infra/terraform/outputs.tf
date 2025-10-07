output "alb_dns_name" {
  description = "DNS name of the application load balancer"
  value       = aws_lb.app.dns_name
}

output "service_url" {
  description = "HTTPS endpoint for the application"
  value       = "https://${var.app_domain_name}"
}

output "assets_distribution_domain" {
  description = "CloudFront distribution domain for static assets"
  value       = aws_cloudfront_distribution.assets.domain_name
}

output "rds_endpoint" {
  description = "PostgreSQL endpoint"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "ssm_parameter_prefix" {
  description = "Prefix for parameters stored in SSM"
  value       = "/wh-ephemeris/${var.environment}"
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.service.repository_url
}
