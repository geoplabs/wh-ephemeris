# Production configuration for wh-ephemeris API deployment.
# Update each value with the real account-specific settings before running terraform plan/apply.

aws_region      = "us-east-1"
environment     = "prod"
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/wh-ephemeris:prod-latest"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
route53_zone_id = "ZABCDEFGHIJKLMNOP"
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
db_password = "CHANGE_ME_WITH_A_SECURE_PASSWORD"
additional_tags = {
  Project     = "wh-ephemeris"
  Environment = "prod"
}
enable_elasticache = false
