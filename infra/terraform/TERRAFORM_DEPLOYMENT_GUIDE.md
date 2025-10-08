# WH-Ephemeris Terraform Deployment Guide

## 🚀 Complete ECS Fargate Deployment for Account 863518458871

This guide provides step-by-step instructions for deploying the WH-Ephemeris API using Terraform with ECS Fargate, integrated with the enhanced Docker image that includes Swiss Ephemeris data.

## 📋 Prerequisites

### 1. AWS Account Setup
- **Account ID**: `863518458871`
- **Region**: `us-east-1` (Mumbai)
- **Required Services**: ECS, ECR, RDS, ALB, Route 53, ACM

### 2. Local Requirements
- **Terraform**: >= 1.4.0
- **AWS CLI**: >= 2.0
- **Docker**: >= 20.0
- **Git**: Latest version

### 3. AWS Permissions
Your AWS user/role needs permissions for:
- ECR (create repositories, push images)
- ECS (create clusters, services, task definitions)
- RDS (create databases, parameter groups)
- VPC (create VPCs, subnets, security groups)
- ALB (create load balancers, target groups)
- Route 53 (create DNS records)
- ACM (use SSL certificates)
- IAM (create roles and policies)

## 🔧 Pre-Deployment Setup

### Step 1: Configure AWS CLI
```bash
# Configure AWS CLI for account 863518458871
aws configure
# Enter your access key, secret key, and set region to us-east-1

# Verify configuration
aws sts get-caller-identity
# Should show Account: 863518458871
```

### Step 2: SSL Certificate Setup
```bash
# Request SSL certificate in ACM (if not already done)
aws acm request-certificate \
  --domain-name "api.whathoroscope.com" \
  --subject-alternative-names "*.whathoroscope.com" \
  --validation-method DNS \
  --region us-east-1

# Note the certificate ARN and update terraform.tfvars
```

### Step 3: Route 53 Hosted Zone
```bash
# Get your hosted zone ID for whathoroscope.com
aws route53 list-hosted-zones --query 'HostedZones[?Name==`whathoroscope.com.`]'

# Note the Zone ID and update terraform.tfvars
```

## 🐳 Build and Push Docker Image

### Step 1: Build Enhanced Docker Image
```bash
# Navigate to project root
cd /path/to/wh-ephemeris

# Make build script executable
chmod +x infra/terraform/build-and-push.sh

# Build and push to ECR (includes Swiss Ephemeris download)
./infra/terraform/build-and-push.sh
```

This script will:
- ✅ Create ECR repository if needed
- ✅ Build Docker image with integrated ephemeris data
- ✅ Push image to ECR
- ✅ Update `terraform.tfvars` with correct image URI

### Step 2: Verify Image
```bash
# List ECR images
aws ecr describe-images \
  --repository-name wh-ephemeris \
  --region us-east-1
```

## 🏗️ Terraform Deployment

### Step 1: Update Configuration
Edit `infra/terraform/terraform.tfvars`:

```hcl
# Update these values for your account
certificate_arn = "arn:aws:acm:us-east-1:863518458871:certificate/YOUR_CERT_ID"
route53_zone_id = "YOUR_HOSTED_ZONE_ID"

# Update API keys for production
app_environment = {
  # ... other vars ...
  API_KEYS = "your-production-api-key-1,your-production-api-key-2"
  JWT_PUBLIC_KEY = "your-jwt-public-key"
  HMAC_SECRET = "your-hmac-secret"
}
```

### Step 2: Initialize Terraform
```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Validate configuration
terraform validate
```

### Step 3: Plan Deployment
```bash
# Review deployment plan
terraform plan

# Save plan for review
terraform plan -out=tfplan
```

### Step 4: Deploy Infrastructure
```bash
# Apply the plan
terraform apply tfplan

# Or apply directly (will prompt for confirmation)
terraform apply
```

**Deployment Time**: ~15-20 minutes

## 🔍 Post-Deployment Verification

### Step 1: Check ECS Service
```bash
# Get cluster status
aws ecs describe-clusters --clusters wh-ephemeris-prod --region us-east-1

# Check service status
aws ecs describe-services \
  --cluster wh-ephemeris-prod \
  --services wh-ephemeris-prod \
  --region us-east-1
```

### Step 2: Test API Endpoints
```bash
# Health check
curl https://api.whathoroscope.com/health

# API documentation
curl https://api.whathoroscope.com/docs

# Test panchang endpoint
curl -X POST https://api.whathoroscope.com/v1/panchang/compute \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "lat": 28.6139,
    "lon": 77.2090,
    "date": "2024-01-15",
    "tz": "Asia/Kolkata"
  }'
```

### Step 3: Monitor Logs
```bash
# View ECS logs
aws logs describe-log-groups --log-group-name-prefix "/ecs/wh-ephemeris" --region us-east-1

# Stream logs
aws logs tail /ecs/wh-ephemeris-prod --follow --region us-east-1
```

## 💰 Cost Optimization

### Current Configuration Costs (Monthly)
- **ECS Fargate**: ~$25-30 (0.25 vCPU, 0.5 GB RAM)
- **RDS PostgreSQL**: ~$15-20 (db.t4g.micro)
- **ALB**: ~$18-22
- **Data Transfer**: ~$2-5
- **CloudWatch Logs**: ~$1-3
- **Total**: ~$61-80/month

### Cost Reduction Options

#### Option 1: Reduce Task Resources
```hcl
# In terraform.tfvars
task_cpu    = 256   # Reduce from 512
task_memory = 512   # Reduce from 1024
```
**Savings**: ~$12-15/month

#### Option 2: Use Spot Instances (ECS on EC2)
```hcl
# Switch to ECS on EC2 with Spot instances
# Requires additional Terraform configuration
```
**Savings**: ~$20-25/month

#### Option 3: Disable RDS (Use SQLite)
```hcl
# In terraform.tfvars
enable_rds = false  # Add this variable
```
**Savings**: ~$15-20/month

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# 1. Build new image
./infra/terraform/build-and-push.sh

# 2. Update ECS service (force new deployment)
aws ecs update-service \
  --cluster wh-ephemeris-prod \
  --service wh-ephemeris-prod \
  --force-new-deployment \
  --region us-east-1
```

### Scaling the Service
```bash
# Scale up
aws ecs update-service \
  --cluster wh-ephemeris-prod \
  --service wh-ephemeris-prod \
  --desired-count 2 \
  --region us-east-1

# Scale down
aws ecs update-service \
  --cluster wh-ephemeris-prod \
  --service wh-ephemeris-prod \
  --desired-count 1 \
  --region us-east-1
```

### Backup and Restore
```bash
# Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier wh-ephemeris-prod \
  --db-snapshot-identifier wh-ephemeris-backup-$(date +%Y%m%d) \
  --region us-east-1
```

## 🚨 Troubleshooting

### Common Issues

#### 1. ECS Tasks Not Starting
```bash
# Check task definition
aws ecs describe-task-definition --task-definition wh-ephemeris-prod --region us-east-1

# Check service events
aws ecs describe-services --cluster wh-ephemeris-prod --services wh-ephemeris-prod --region us-east-1
```

#### 2. ALB Health Check Failures
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn YOUR_TARGET_GROUP_ARN --region us-east-1

# Common fixes:
# - Verify container port (8080)
# - Check health check path (/health)
# - Verify security group rules
```

#### 3. Database Connection Issues
```bash
# Test database connectivity from ECS task
aws ecs execute-command \
  --cluster wh-ephemeris-prod \
  --task TASK_ID \
  --container app \
  --interactive \
  --command "/bin/bash" \
  --region us-east-1
```

#### 4. Swiss Ephemeris Data Missing
```bash
# Verify ephemeris files in container
docker run --rm -it 863518458871.dkr.ecr.us-east-1.amazonaws.com/wh-ephemeris:prod-latest \
  ls -la /opt/app/data/ephemeris/

# Should show:
# - seas_18.se1
# - semo_18.se1  
# - sepl_18.se1
# - de406.eph
```

## 🔐 Security Best Practices

### 1. API Key Management
- Store API keys in AWS Systems Manager Parameter Store
- Rotate keys regularly
- Use different keys for different environments

### 2. Network Security
- ECS tasks run in private subnets (if configured)
- ALB handles public traffic
- Database in private subnets only

### 3. SSL/TLS
- ALB terminates SSL
- Use TLS 1.2+ only
- Certificate auto-renewal via ACM

## 📊 Monitoring and Alerts

### CloudWatch Metrics
- ECS service CPU/Memory utilization
- ALB request count and latency
- RDS connections and performance

### Recommended Alarms
```bash
# High CPU utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "wh-ephemeris-high-cpu" \
  --alarm-description "ECS CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

## 🎉 Success Checklist

- ✅ Docker image built with integrated ephemeris data
- ✅ ECR repository created and image pushed
- ✅ Terraform infrastructure deployed
- ✅ ECS service running and healthy
- ✅ ALB health checks passing
- ✅ API endpoints responding correctly
- ✅ SSL certificate configured
- ✅ DNS records pointing to ALB
- ✅ Monitoring and logging configured

## 📞 Support

For issues with this deployment:

1. **Check CloudWatch Logs**: `/ecs/wh-ephemeris-prod`
2. **Review ECS Service Events**: AWS Console → ECS → Services
3. **Verify ALB Target Health**: AWS Console → EC2 → Load Balancers
4. **Test Database Connectivity**: Use ECS Exec or CloudShell

Your WH-Ephemeris API is now running on production-grade AWS infrastructure with integrated Swiss Ephemeris data! 🚀
