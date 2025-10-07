variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}

variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "public_subnets" {
  description = "Map of public subnet definitions"
  type = map(object({
    cidr = string
    az   = string
  }))
  default = {
    a = {
      cidr = "10.10.1.0/24"
      az   = "us-east-1a"
    }
    b = {
      cidr = "10.10.2.0/24"
      az   = "us-east-1b"
    }
  }
}

variable "private_subnets" {
  description = "Map of private subnet definitions"
  type = map(object({
    cidr = string
    az   = string
  }))
  default = {
    a = {
      cidr = "10.10.11.0/24"
      az   = "us-east-1a"
    }
    b = {
      cidr = "10.10.12.0/24"
      az   = "us-east-1b"
    }
  }
}

variable "container_image" {
  description = "Full image URI for the WH-Ephemeris container"
  type        = string
}

variable "container_port" {
  description = "Application container listening port"
  type        = number
  default     = 8080
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory"
  type        = number
  default     = 1024
}

variable "desired_task_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 2
}

variable "autoscaling_cpu_target" {
  description = "CPU utilization target for auto scaling"
  type        = number
  default     = 65
}

variable "health_check_path" {
  description = "HTTP path for load balancer health checks"
  type        = string
  default     = "/__health"
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
}

variable "route53_zone_id" {
  description = "Hosted zone ID for whathoroscope.com"
  type        = string
}

variable "app_domain_name" {
  description = "Record name for the application (e.g., api.whathoroscope.com)"
  type        = string
  default     = "api.whathoroscope.com"
}

variable "assets_bucket_name" {
  description = "Name for the public assets bucket"
  type        = string
}

variable "assets_cnames" {
  description = "Alternative domain names for the assets distribution"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period"
  type        = number
  default     = 30
}

variable "app_environment" {
  description = "Plaintext environment variables injected into the ECS task"
  type        = map(string)
  default     = {}
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.5"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_backup_retention" {
  description = "Backup retention period in days"
  type        = number
  default     = 3
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot on destroy"
  type        = bool
  default     = false
}

variable "db_deletion_protection" {
  description = "Enable RDS deletion protection"
  type        = bool
  default     = true
}

variable "db_name" {
  description = "Initial database name"
  type        = string
  default     = "ephemeris"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "ephuser"
}

variable "db_password" {
  description = "Master database password"
  type        = string
  sensitive   = true
}

variable "enable_elasticache" {
  description = "Whether to provision a Redis cluster"
  type        = bool
  default     = false
}

variable "redis_node_type" {
  description = "Instance size for Redis"
  type        = string
  default     = "cache.t4g.micro"
}

variable "enable_container_insights" {
  description = "Enable ECS container insights"
  type        = bool
  default     = true
}
