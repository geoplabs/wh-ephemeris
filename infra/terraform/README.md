# WH-Ephemeris AWS Infrastructure (Terraform)

This Terraform configuration provisions a minimal-yet-production ready footprint for the WH-Ephemeris service inside AWS. The design keeps the monthly spend in the USD 30–50 band by using the smallest recommended instance sizes, single-AZ RDS, on-demand Fargate tasks, and optional Redis caching.

## Architecture

The stack deploys the following AWS resources:

- **Networking:** single VPC with two public subnets for ingress/ECS and two private subnets for the database (no NAT Gateway to avoid recurring charges).
- **Compute:** ECS Fargate service running the WH-Ephemeris container image with autoscaling from 1–2 tasks.
- **Load balancing:** Internet-facing Application Load Balancer terminating HTTPS with an existing ACM certificate.
- **Data:** Amazon RDS PostgreSQL (db.t4g.micro, single AZ). Redis (cache.t4g.micro) is optional and disabled by default.
- **Storage & assets:** S3 bucket backed by a low-cost CloudFront distribution (Price Class 100) for serving static assets under `whathoroscope.com` aliases.
- **Observability & secrets:** CloudWatch log group, SSM Parameter Store parameters for application secrets, and ECR repository for images.
- **DNS:** Route 53 record to map `api.whathoroscope.com` to the ALB.

## Prerequisites

- Terraform >= 1.4.0
- AWS credentials with permissions to create the resources listed above
- Ownership of the `whathoroscope.com` domain in Namecheap (or the current registrar)
- Production site hosted on Vercel under `whathoroscope.com`
- An issued ACM certificate in `us-east-1` that includes `api.whathoroscope.com`
- WH-Ephemeris container image published to (or to be published to) Amazon ECR

### DNS Preparation (Namecheap + Vercel → AWS)

Because the apex domain stays on Vercel while the API is hosted in AWS, the Terraform code needs a Route 53 hosted zone that is delegated just for the API subdomain. Complete these steps **before** running Terraform:

1. **Create a public hosted zone** in Route 53 named `api.whathoroscope.com` (or the subdomain you plan to use). Copy the four name servers AWS assigns to the zone.
2. **Delegate the subdomain from Namecheap**: in the Namecheap DNS panel for `whathoroscope.com`, add an `NS` record with host `api` (or your chosen prefix) that lists the four Route 53 name servers. This leaves the apex/root records under Namecheap/Vercel control while handing `api.whathoroscope.com` to Route 53.
3. **Update your ACM certificate validation** if necessary so that the DNS validation CNAMEs resolve under the delegated Route 53 zone.
4. Once delegation propagates (usually within minutes, but can take up to 24 hours), `dig api.whathoroscope.com NS` should return the Route 53 name servers. You can then pass the hosted zone ID to Terraform via `route53_zone_id`.

If you prefer to move the entire domain into Route 53 you can do so instead, but that is not required as long as the API subdomain is delegated to AWS.

## Usage

1. Copy the example variables file and update it with project-specific values:

   ```bash
   cd infra/terraform
   cp terraform.tfvars.example terraform.tfvars
   # edit terraform.tfvars with the correct account IDs, certificate ARN, passwords, etc.
   ```

2. Initialise Terraform:

   ```bash
   terraform init
   ```

3. Review the plan:

   ```bash
   terraform plan
   ```

4. Apply the changes:

   ```bash
   terraform apply
   ```

5. After the apply completes, note the outputs for the load balancer DNS name, CloudFront distribution, and SSM parameter prefix. These values are required when deploying application updates.

## Cost Notes

- ECS Fargate (0.5 vCPU / 1 GiB) running a single task plus the Application Load Balancer accounts for the bulk of the cost but stays within the monthly target.
- The RDS `db.t4g.micro` instance runs in a single Availability Zone to reduce charges. Multi-AZ can be enabled later by setting `multi_az` on the database resource if higher availability is required.
- Redis is disabled by default. Set `enable_elasticache = true` if caching is needed and the budget allows the additional spend.
- NAT Gateways are intentionally omitted. If private workloads need outbound internet access, consider using VPC endpoints or enabling a single NAT Gateway with awareness of the added ~$30/month expense.

## Next Steps

- Push the application container to the created ECR repository (see the `ecr_repository_url` output).
- Configure the WH-Ephemeris task’s environment variables/secrets beyond the database values by adding additional SSM parameters under `/wh-ephemeris/<environment>/`.
- Update DNS for static assets (e.g., `assets.whathoroscope.com`) to point to the CloudFront distribution returned in the outputs.

