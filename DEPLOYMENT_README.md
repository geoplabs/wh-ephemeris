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

### 3. 💰 AWS Minimal (Cost-Optimized)

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

| Feature | Vercel | AWS Minimal | AWS Production |
|---------|--------|-------------|----------------|
| **Setup Time** | 10 min | 30 min | 2-4 hours |
| **Monthly Cost** | $0-25 | $3-8 | $100-200 |
| **Scalability** | Auto | Manual | Auto |
| **Availability** | High | Medium | Very High |
| **Maintenance** | None | Low | Medium |
| **Performance** | Good | Medium | Excellent |
| **Global CDN** | ✅ | ❌ | ✅ |
| **Custom Domain** | ✅ | ✅ | ✅ |
| **SSL/HTTPS** | Auto | Manual | Auto |
| **Monitoring** | Built-in | Basic | Advanced |
| **Backup** | N/A | Manual | Automated |

## 🎯 Decision Matrix

**Choose Vercel if**:
- You want the fastest deployment
- You have low to medium traffic
- You don't need persistent storage
- You want zero maintenance

**Choose AWS Minimal if**:
- You have budget constraints
- You need persistent storage
- You're comfortable with basic server management
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
