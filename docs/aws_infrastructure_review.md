# WH-Ephemeris AWS Infrastructure Guide Review

This document highlights the material omissions in the "AWS Infrastructure Setup Guide" that was provided for the WH-Ephemeris production environment. The intent is to surface the gaps that must be closed before the instructions can be considered production-ready.

## 1. Governance, Accounts, and IAM
- No guidance on organizational setup (AWS Organizations, account separation for prod/staging) or baseline guardrails (Service Control Policies, billing alarms). This is critical for production governance.
- IAM roles and policies for each workload component are missing (ECS task execution/task roles, Lambda roles, RDS access roles, SSM access policies, EFS mount permissions). Without them, the services cannot interact securely.
- There is no mention of KMS CMKs for encrypting data at rest (RDS, EFS, S3, Systems Manager secure parameters) or for TLS offload.

## 2. Networking and Connectivity
- The VPC section provisions only one NAT Gateway in one AZ. For a multi-AZ, highly available architecture a NAT Gateway is required in each AZ plus distinct private route tables.
- No Network ACL guidance or mention of VPC Flow Logs to support troubleshooting and security monitoring.
- DNS private hosted zones, Route 53 health checks, and record configuration (A/AAAA/CNAME/alias records pointing to CloudFront or ALB) are absent.

## 3. Compute (ECS, Lambda) Configuration
- The guide does not create an ECS cluster, capacity providers, task definitions, or services. Auto-scaling policies, deployment strategies, and desired count configuration are missing.
- There is no description of how the containers obtain the application image (ECR auth, lifecycle policies) or how environment variables/secrets are injected.
- Lambda integration via API Gateway is mentioned as optional but lacks instructions on provisioning the function, execution role, deployment package, and integration responses.

## 4. Application Routing and Edge Services
- CloudFront configuration is absent (origin configuration, behaviors, TLS policies, WAF integration, logging). Merely listing the service is insufficient.
- Route 53 and ACM steps stop at certificate request; DNS validation, record creation, and certificate attachment to CloudFront/ALB listeners are not covered.
- There is no AWS WAF or Shield guidance, nor mention of rate limiting or bot protection.

## 5. Data Stores and Persistence
- RDS setup omits subnet group AZ coverage verification, parameter groups, performance insights, automated backup configuration review, and read replica/disaster recovery planning.
- ElastiCache is provisioned as a single-node cluster with no replication group, automatic failover, backups, or security hardening guidance.
- EFS throughput configuration ignores lifecycle management, access points, and backup policies; mount helper (TLS) instructions are also missing.

## 6. Storage and Content Management
- S3 buckets lack versioning, server access logging, lifecycle policies, default encryption, and explicit public access block settings.
- No guidance on pre-signed URLs or access control for private report downloads.
- Artifact management for build assets (e.g., using CodeArtifact or S3 for container build context) is not addressed.

## 7. Security, Secrets, and Compliance
- Secrets Manager vs. SSM Parameter Store trade-offs are not discussed; rotation policies and KMS encryption keys are missing.
- Security group egress rules, least-privilege principles, and cross-service access (e.g., ALB to ECS, ECS to RDS) require explicit documentation.
- There is no coverage of compliance requirements such as logging retention, audit trails, or GDPR considerations for stored user data.

## 8. Observability and Operations
- CloudWatch section lacks log group creation, retention policies, metrics/alarms (CPU, memory, latency, errors), dashboards, and alerting via SNS/PagerDuty.
- There is no mention of distributed tracing (X-Ray), container insights, or structured application logging.
- Operational runbooks, incident response procedures, and health-check endpoint descriptions are missing.

## 9. Automation and CI/CD
- The guide provides manual CLI commands only; infrastructure-as-code (CDK, CloudFormation, Terraform) definitions are absent despite `npm install -g aws-cdk` being recommended.
- CI/CD pipelines (CodePipeline, GitHub Actions) to build, test, and deploy container images to ECS are not described.
- Drift detection, change management, and environment promotion workflows are missing.

## 10. Cost Management
- Cost estimate of $30-50/month is unrealistic for the proposed architecture (multi-AZ RDS, NAT Gateway, CloudFront, etc.) and lacks a detailed breakdown or cost-optimization guidance.
- No cost monitoring (Cost Explorer, budgets, anomaly detection) or tagging standards are provided.

## 11. Business Continuity and Disaster Recovery
- Backup and restore procedures for RDS, EFS, and S3 are not documented.
- There is no disaster recovery plan (e.g., cross-region replication, pilot-light environments).
- High-availability testing, chaos engineering, and recovery time objectives (RTO/RPO) are not addressed.

These gaps should be resolved to ensure the infrastructure guide enables a secure, reliable, and maintainable production deployment.
