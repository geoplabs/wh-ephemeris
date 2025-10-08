# Production configuration for wh-ephemeris API deployment.
# Update each value with the real account-specific settings before running terraform plan/apply.

aws_region      = "us-east-1"
environment     = "prod"
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/wh-ephemeris:prod-latest"
certificate_arn = "arn:aws:acm:us-east-1:863518458871:certificate/e8b770ae-6e4c-40cf-8ec9-54e6f762dc56"
route53_zone_id = "Z0822624UBELBP4YU02I"
app_domain_name = "api.whathoroscope.com"
assets_bucket_name = "wh-ephemeris-assets-prod"
assets_cnames = [
  "assets.whathoroscope.com",
]
app_environment = {
  AUTH_ENABLED       = "true"
  API_KEYS           = "replace-with-comma-separated-production-keys"
  RATE_LIMIT_ENABLED = "true"
  LOGGING_ENABLED    = "true"
}
db_password = "w#@ts3cureP@ssw0rd!"
additional_tags = {
  Project     = "wh-ephemeris"
  Environment = "prod"
}
enable_elasticache = false
