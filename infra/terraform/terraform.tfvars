# Production configuration for wh-ephemeris API deployment.
# Updated for account 863518458871 with FastAPI configuration

aws_region      = "us-east-1"  # NVirginia region for account 863518458871
environment     = "prod"
container_image = "863518458871.dkr.ecr.us-east-1.amazonaws.com/wh-ephemeris:prod-latest"
certificate_arn = "arn:aws:acm:us-east-1:863518458871:certificate/e8b770ae-6e4c-40cf-8ec9-54e6f762dc56"
route53_zone_id = "Z0822624UBELBP4YU02I"
app_domain_name = "api.whathoroscope.com"
assets_bucket_name = "wh-ephemeris-assets-prod-863518458871"  # Must be globally unique
assets_cnames = [
  "assets.whathoroscope.com",
]

# FastAPI Environment Variables (based on codebase analysis)
app_environment = {
  # Core Application
  APP_ENV                = "production"
  PORT                   = "8080"
  
  # Authentication & Security
  AUTH_ENABLED          = "true"
  API_KEYS              = "pHSbj2vjJ+rUprhF2W2B3acz6QCLdEOdFmb1yzuGWPE="
  RATE_LIMIT_ENABLED    = "true"
  RATE_LIMIT_PER_MINUTE = "60"
  LOGGING_ENABLED       = "true"
  
  # Ephemeris Configuration
  EPHEMERIS_BACKEND     = "swieph"
  EPHEMERIS_DIR         = "/opt/app/data/ephemeris"
  
  # Astrology Defaults (based on codebase analysis)
  DEFAULT_AYANAMSHA     = "lahiri"
  DEFAULT_WESTERN_HOUSE = "placidus"
  DEFAULT_VEDIC_HOUSE   = "whole_sign"
  UNKNOWN_TIME_POLICY   = "solar_whole_sign"
  INCLUDE_CHIRON        = "true"
  ALLOW_GEMSTONES       = "true"
  
  # Place Defaults (New Delhi - matches codebase defaults)
  DEFAULT_PLACE_LAT     = "28.6139"
  DEFAULT_PLACE_LON     = "77.2090"
  DEFAULT_PLACE_TZ      = "Asia/Kolkata"
  DEFAULT_PLACE_LABEL   = "New Delhi, India"
  
  # PDF Generation
  USE_WEASY            = "true"
  
  # API Configuration
  NATAL_USE_HTTP       = "false"
}

db_password = "w#@ts3cureP@ssw0rd!"
additional_tags = {
  Project     = "wh-ephemeris"
  Environment = "prod"
  Account     = "863518458871"
}
enable_elasticache = false  # Start without Redis for cost optimization
