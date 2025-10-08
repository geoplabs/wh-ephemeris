# Environment Variables Analysis for WH-Ephemeris

## 🔍 **Current Environment Variables Found in Codebase**

### **Authentication & Security**
- `AUTH_ENABLED` - Enable/disable API key authentication (default: "false")
- `API_KEYS` - Comma-separated list of valid API keys
- `RATE_LIMIT_ENABLED` - Enable/disable rate limiting (default: "false") 
- `RATE_LIMIT_PER_MINUTE` - Rate limit per minute (default: "10")

### **Application Configuration**
- `APP_ENV` - Application environment (production/development)
- `PORT` - Server port (default: 8080)
- `LOGGING_ENABLED` - Enable/disable request logging (default: "false")

### **Ephemeris Configuration**
- `EPHEMERIS_BACKEND` - Backend type: "swieph" or "moseph" (default: "swieph")
- `EPHEMERIS_DIR` - Directory path for ephemeris files

### **Astrology Defaults**
- `DEFAULT_PLACE_LAT` - Default latitude (default: "28.6139" - New Delhi)
- `DEFAULT_PLACE_LON` - Default longitude (default: "77.2090" - New Delhi)
- `DEFAULT_PLACE_TZ` - Default timezone (default: "Asia/Kolkata")
- `DEFAULT_PLACE_LABEL` - Default place label (default: "New Delhi, India")

### **AWS Configuration (for LocalStack/Production)**
- `AWS_REGION` - AWS region (default: "us-east-1")
- `AWS_ENDPOINT_URL` - AWS endpoint URL (for LocalStack)
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `S3_BUCKET` - S3 bucket name (default: "wh-reports-dev")
- `SQS_QUEUE` - SQS queue name (default: "wh-reports-jobs")

## 🚨 **Missing Environment Variables in Current terraform.tfvars**

Based on the codebase analysis, the following environment variables are **MISSING** from your current `terraform.tfvars`:

### **Critical Missing Variables**
1. **`JWT_PUBLIC_KEY`** - Referenced in tfvars but not used in code
2. **`JWT_ISS`** - Referenced in tfvars but not used in code  
3. **`JWT_AUD`** - Referenced in tfvars but not used in code
4. **`HMAC_SECRET`** - Referenced in tfvars but not used in code

### **Important Missing Variables**
5. **`DEFAULT_WESTERN_HOUSE`** - Default house system for Western astrology
6. **`DEFAULT_VEDIC_HOUSE`** - Default house system for Vedic astrology  
7. **`UNKNOWN_TIME_POLICY`** - Policy for unknown birth times
8. **`INCLUDE_CHIRON`** - Whether to include Chiron in calculations
9. **`ALLOW_GEMSTONES`** - Whether to allow gemstone recommendations
10. **`USE_WEASY`** - Whether to use WeasyPrint for PDF generation
11. **`NATAL_USE_HTTP`** - Whether to use HTTP for natal calculations

### **Place Defaults**
12. **`DEFAULT_PLACE_LAT`** - Default latitude for calculations
13. **`DEFAULT_PLACE_LON`** - Default longitude for calculations  
14. **`DEFAULT_PLACE_TZ`** - Default timezone
15. **`DEFAULT_PLACE_LABEL`** - Default place label

### **AWS/Database Configuration**
16. **`DATABASE_URL`** - Database connection string
17. **`REDIS_URL`** - Redis connection string (if using Redis)
18. **`S3_BUCKET`** - S3 bucket for file storage
19. **`SQS_QUEUE`** - SQS queue for background jobs

## ✅ **Updated terraform.tfvars Configuration**

Here's what your `app_environment` section should look like:

```hcl
app_environment = {
  # Core Application
  APP_ENV                = "production"
  PORT                   = "8080"
  
  # Authentication & Security
  AUTH_ENABLED          = "true"
  API_KEYS              = "replace-with-comma-separated-production-keys"
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
  
  # Remove these - not used in codebase
  # JWT_AUD              = "whathoroscope"
  # JWT_ISS              = "wh-ephemeris-prod"
}
```

## 🔧 **Database Configuration**

You'll also need to add database environment variables. These should be stored in **AWS Systems Manager Parameter Store** for security:

```hcl
# Add to main.tf secrets section:
{
  name      = "DATABASE_URL"
  valueFrom = aws_ssm_parameter.database_url.arn
},
{
  name      = "REDIS_URL"  
  valueFrom = aws_ssm_parameter.redis_url.arn
},
{
  name      = "S3_BUCKET"
  valueFrom = aws_ssm_parameter.s3_bucket.arn
}
```

## 🎯 **Action Items**

1. **Remove unused JWT/HMAC variables** - These aren't used in the current codebase
2. **Add missing astrology defaults** - Critical for proper chart calculations
3. **Add place defaults** - Ensures consistent fallback behavior
4. **Configure database secrets** - Store sensitive data in Parameter Store
5. **Update API keys** - Replace placeholder with real production keys

## 🔍 **Verification Commands**

After updating, verify the configuration:

```bash
# Check environment variables in running container
aws ecs execute-command \
  --cluster wh-ephemeris-prod \
  --task TASK_ID \
  --container app \
  --interactive \
  --command "env | grep -E '(EPHEMERIS|DEFAULT|AUTH)'" \
  --region us-east-1
```

This analysis shows that your current `terraform.tfvars` is missing several critical environment variables that the application expects. The JWT/HMAC variables you have are not actually used by the current codebase.
