# 🚀 WH-Ephemeris Deployment Options

This project supports multiple deployment strategies to meet different needs and budgets.

## 📁 Project Structure

```
wh-ephemeris/
├── api/                          # Main FastAPI application
├── data/                         # Application data and assets
├── tests/                        # Test suite
├── aws/                          # AWS deployment files
│   ├── AWS_INFRASTRUCTURE_GUIDE.md
│   ├── AWS_BUILD_DEPLOYMENT_GUIDE.md
│   ├── *.sh                      # Deployment scripts
│   ├── *.conf                    # Configuration files
│   └── requirements_*.txt        # AWS-specific requirements
├── vercel/                       # Vercel deployment files
│   ├── VERCEL_DEPLOYMENT_GUIDE.md
│   ├── vercel.json              # Vercel configuration
│   ├── vercel_app.py            # Vercel entry point
│   ├── vercel_middleware.py     # Serverless optimizations
│   ├── requirements.txt         # Vercel requirements
│   ├── package.json             # Node.js metadata
│   └── .vercelignore           # Deployment exclusions
└── DEPLOYMENT_README.md         # This file
```

## 🎯 Deployment Options

### 1. 🌐 Vercel (Recommended for Quick Start)

**Best for**: Rapid deployment, global CDN, automatic scaling

**Pros**:
- ✅ Serverless - no server management
- ✅ Global CDN with edge locations
- ✅ Automatic HTTPS and custom domains
- ✅ Zero downtime deployments
- ✅ Built-in analytics and monitoring
- ✅ Git-based deployments

**Cons**:
- ❌ 30-second timeout limit
- ❌ Cold starts for first requests
- ❌ Limited to 1GB RAM per function
- ❌ No persistent storage

**Cost**: $0-25/month (traffic dependent)

**Setup Time**: 10-15 minutes

**Guide**: [Vercel Deployment Guide](./vercel/VERCEL_DEPLOYMENT_GUIDE.md)

---

### 2. ☁️ AWS Production (Enterprise Grade)

**Best for**: Production workloads, high availability, enterprise requirements

**Pros**:
- ✅ Full control over infrastructure
- ✅ High availability across multiple AZs
- ✅ Auto-scaling with ECS Fargate
- ✅ Managed databases (RDS, ElastiCache)
- ✅ Advanced monitoring and logging
- ✅ Enterprise security features

**Cons**:
- ❌ Complex setup and management
- ❌ Higher costs
- ❌ Requires AWS expertise
- ❌ More moving parts to maintain

**Cost**: $100-200/month

**Setup Time**: 2-4 hours

**Guides**:
- [AWS Infrastructure Guide](./aws/AWS_INFRASTRUCTURE_GUIDE.md)
- [AWS Build & Deployment Guide](./aws/AWS_BUILD_DEPLOYMENT_GUIDE.md)

---

### 3. ☁️ AWS Production (Fargate Budget)

**Best for**: Production workloads that must stay within a $30-50/month AWS budget while integrating with `whathoroscope.com`.

**Pros**:
- ✅ Managed Fargate compute with HTTPS via Application Load Balancer
- ✅ RDS PostgreSQL (single-AZ) and optional ElastiCache
- ✅ CloudFront + S3 for static assets under the project domain
- ✅ Terraform automation for repeatable deployments
- ✅ Secrets stored in SSM Parameter Store

**Cons**:
- ❌ Limited capacity (1–2 Fargate tasks by default)
- ❌ Manual horizontal scaling beyond the configured autoscaling range
- ❌ NAT Gateway omitted (private subnet egress requires VPC endpoints or later upgrades)

**Cost**: $30-50/month

**Setup Time**: 60-90 minutes

**Files**: [`infra/terraform`](./infra/terraform) – see the accompanying [README](./infra/terraform/README.md) for step-by-step usage.

**DNS prerequisites when the main site stays on Vercel**:

- Keep `whathoroscope.com` pointed to Vercel in Namecheap.
- Create a public Route 53 hosted zone just for `api.whathoroscope.com` (or your chosen API subdomain) and note the hosted zone ID.
- Add an `NS` record in Namecheap with host `api` that delegates the subdomain to the Route 53 name servers.
- Issue/validate an ACM certificate in `us-east-1` that includes the delegated API subdomain so the Application Load Balancer can terminate HTTPS.
- After DNS propagation, supply the hosted zone ID and certificate ARN to Terraform via `terraform.tfvars`.

---

### 4. 💰 AWS Minimal (Cost-Optimized)

**Best for**: Small-scale production, budget constraints, testing

**Pros**:
- ✅ Single EC2 instance deployment
- ✅ Local SQLite database
- ✅ Local Redis caching
- ✅ Nginx reverse proxy
- ✅ Cost-effective for low traffic

**Cons**:
- ❌ Single point of failure
- ❌ Manual scaling required
- ❌ Limited to one availability zone
- ❌ More maintenance required

**Cost**: $3-8/month

**Setup Time**: 30-60 minutes

**Files**: Available in `./aws/` folder (deployment scripts)

---

## 🚀 Quick Start Recommendations

### For Development/Testing:
```bash
# Use Vercel for fastest deployment
cd vercel/
# Follow VERCEL_DEPLOYMENT_GUIDE.md
```

### For Production (Small Scale):
```bash
# Use AWS Minimal deployment
cd aws/
# Run deployment scripts
```

### For Production (Managed on a Budget):
```bash
# Use Terraform-based Fargate stack (targets $30-50/month)
cd infra/terraform
terraform init
terraform apply
```

### For Production (Enterprise):
```bash
# Use full AWS infrastructure
cd aws/
# Follow AWS_INFRASTRUCTURE_GUIDE.md first
# Then AWS_BUILD_DEPLOYMENT_GUIDE.md
```

## 🔧 Configuration

### Environment Variables (All Deployments)

```bash
# Core Configuration
APP_ENV=production
JWT_AUD=whathoroscope
JWT_ISS=wh-ephemeris

# Security
JWT_PUBLIC_KEY=your-jwt-public-key
HMAC_SECRET=your-hmac-secret
API_KEYS=your-api-keys

# Features
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
LOGGING_ENABLED=true

# Astrology Settings
DEFAULT_WESTERN_HOUSE=placidus
DEFAULT_VEDIC_HOUSE=whole_sign
DEFAULT_AYANAMSHA=lahiri
INCLUDE_CHIRON=true
ALLOW_GEMSTONES=true
UNKNOWN_TIME_POLICY=solar_whole_sign

# Ephemeris Configuration
EPHEMERIS_BACKEND=swieph
EPHEMERIS_DIR=/path/to/ephemeris
NATAL_USE_HTTP=false
```

## 📊 Feature Comparison

| Feature | Vercel | AWS Minimal | AWS Fargate Budget | AWS Production |
|---------|--------|-------------|--------------------|----------------|
| **Setup Time** | 10 min | 30-60 min | 60-90 min | 2-4 hours |
| **Monthly Cost** | $0-25 | $3-8 | $30-50 | $100-200 |
| **Scalability** | Auto | Manual | Auto (1-2 tasks) | Auto |
| **Availability** | High | Medium | High | Very High |
| **Maintenance** | None | Low | Low | Medium |
| **Performance** | Good | Medium | Good | Excellent |
| **Global CDN** | ✅ | ❌ | ✅ | ✅ |
| **Custom Domain** | ✅ | ✅ | ✅ | ✅ |
| **SSL/HTTPS** | Auto | Manual | Auto | Auto |
| **Monitoring** | Built-in | Basic | CloudWatch | Advanced |
| **Backup** | N/A | Manual | Automated (RDS) | Automated |

## 🎯 Decision Matrix

**Choose Vercel if**:
- You want the fastest deployment
- You have low to medium traffic
- You don't need persistent storage
- You want zero maintenance

**Choose AWS Minimal if**:
- You have strict budget constraints (<$10/month)
- You need persistent storage without managed services
- You're comfortable with basic server management

**Choose AWS Fargate Budget if**:
- You need managed container hosting with HTTPS on `whathoroscope.com`
- You want managed PostgreSQL and optional Redis without exceeding $50/month
- You prefer infrastructure-as-code (Terraform) for reproducible deployments
- You have predictable, low traffic

**Choose AWS Production if**:
- You need enterprise-grade reliability
- You have high traffic requirements
- You need advanced monitoring and logging
- You have dedicated DevOps resources

## 🔗 Integration with WhatHoroscope.com

All deployment options provide the same API endpoints for integration:

```javascript
// Example integration
const API_BASE = 'https://your-deployment-url.com';
const API_KEY = 'your-api-key';

// Fetch today's Panchang
const response = await fetch(
  `${API_BASE}/v1/panchang/today?lat=28.6139&lon=77.2090`,
  {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    }
  }
);
```

## 📞 Support

- **Vercel Issues**: Check [Vercel Documentation](https://vercel.com/docs)
- **AWS Issues**: Check AWS guides in `./aws/` folder
- **API Issues**: Refer to [Panchang System Documentation](./PANCHANG_SYSTEM_DOCUMENTATION.md)

---

**Choose your deployment strategy and follow the corresponding guide to get started! 🚀**
