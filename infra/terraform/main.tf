terraform {
  required_version = ">= 1.4.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  project_name = "wh-ephemeris"
  tags = merge(
    {
      Project     = local.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.additional_tags
  )
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-vpc"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-igw"
  })
}

resource "aws_subnet" "public" {
  for_each = var.public_subnets

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr
  availability_zone       = each.value.az
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-public-${each.key}"
  })
}

resource "aws_subnet" "private" {
  for_each = var.private_subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-private-${each.key}"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name        = "${local.project_name}-${var.environment}-alb"
  description = "Allow web traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-alb-sg"
  })
}

resource "aws_security_group" "ecs" {
  name        = "${local.project_name}-${var.environment}-ecs"
  description = "Allow traffic from ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "App traffic"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-ecs-sg"
  })
}

resource "aws_security_group" "rds" {
  name        = "${local.project_name}-${var.environment}-rds"
  description = "Allow postgres from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-rds-sg"
  })
}

resource "aws_security_group" "redis" {
  count       = var.enable_elasticache ? 1 : 0
  name        = "${local.project_name}-${var.environment}-redis"
  description = "Allow redis from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-redis-sg"
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.project_name}-${var.environment}-db-subnets"
  subnet_ids = [for s in aws_subnet.private : s.id]

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-db-subnets"
  })
}

resource "aws_db_instance" "postgres" {
  identifier              = "${local.project_name}-${var.environment}-db"
  engine                  = "postgres"
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  db_name                 = var.db_name
  username                = var.db_username
  password                = var.db_password
  backup_retention_period = var.db_backup_retention
  skip_final_snapshot     = var.db_skip_final_snapshot
  deletion_protection     = var.db_deletion_protection
  publicly_accessible     = false
  storage_encrypted       = true
  multi_az                = false
  vpc_security_group_ids  = [aws_security_group.rds.id]
  db_subnet_group_name    = aws_db_subnet_group.main.name
  apply_immediately       = true
  auto_minor_version_upgrade = true
}

resource "aws_s3_bucket" "assets" {
  bucket = var.assets_bucket_name

  tags = merge(local.tags, {
    Name = "${local.project_name}-${var.environment}-assets"
  })
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.assets.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.assets.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_cloudfront_distribution.assets]
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

resource "aws_ecr_repository" "service" {
  name = "${local.project_name}/${var.environment}"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.project_name}-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.project_name}-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "ecs_task_ssm" {
  name = "${local.project_name}-${var.environment}-ecs-ssm"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/wh-ephemeris/*"
        ]
      }
    ]
  })
}

resource "aws_ssm_parameter" "db_host" {
  name  = "/wh-ephemeris/${var.environment}/db/host"
  type  = "String"
  value = aws_db_instance.postgres.address
}

resource "aws_ssm_parameter" "db_name" {
  name  = "/wh-ephemeris/${var.environment}/db/name"
  type  = "String"
  value = var.db_name
}

resource "aws_ssm_parameter" "db_username" {
  name  = "/wh-ephemeris/${var.environment}/db/username"
  type  = "String"
  value = var.db_username
}

resource "aws_ssm_parameter" "db_password" {
  name  = "/wh-ephemeris/${var.environment}/db/password"
  type  = "SecureString"
  value = var.db_password
}

resource "aws_ssm_parameter" "redis_host" {
  count = var.enable_elasticache ? 1 : 0
  name  = "/wh-ephemeris/${var.environment}/redis/endpoint"
  type  = "String"
  value = aws_elasticache_cluster.redis[0].cache_nodes[0].address
}

resource "aws_ssm_parameter" "assets_bucket" {
  name  = "/wh-ephemeris/${var.environment}/s3/assets_bucket"
  type  = "String"
  value = aws_s3_bucket.assets.bucket
}

resource "aws_cloudfront_origin_access_control" "assets" {
  name                              = "${local.project_name}-${var.environment}-oac"
  description                       = "Access control for assets bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "no-override"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "assets" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.project_name}-${var.environment}-assets"
  default_root_object = "index.html"

  aliases = var.assets_cnames

  origin {
    domain_name              = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id                = "s3-assets"
    origin_access_control_id = aws_cloudfront_origin_access_control.assets.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-assets"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    compress               = true
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.certificate_arn
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = local.tags
}

resource "aws_lb" "app" {
  name               = "${local.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for s in aws_subnet.public : s.id]

  tags = local.tags
}

resource "aws_lb_target_group" "app" {
  name        = "${local.project_name}-${var.environment}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    matcher             = "200-399"
    interval            = 30
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
  }

  tags = local.tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = var.app_domain_name
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

resource "aws_ecs_cluster" "main" {
  name = "${local.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = local.tags
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.project_name}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.container_image
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort       = var.container_port
          protocol       = "tcp"
        }
      ]
      environment = [
        for key, value in var.app_environment : {
          name  = key
          value = value
        }
      ]
      secrets = [
        {
          name      = "DATABASE_HOST"
          valueFrom = aws_ssm_parameter.db_host.arn
        },
        {
          name      = "DATABASE_NAME"
          valueFrom = aws_ssm_parameter.db_name.arn
        },
        {
          name      = "DATABASE_USER"
          valueFrom = aws_ssm_parameter.db_username.arn
        },
        {
          name      = "DATABASE_PASSWORD"
          valueFrom = aws_ssm_parameter.db_password.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "app" {
  name            = "${local.project_name}-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_task_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [for s in aws_subnet.public : s.id]
    security_groups = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [
    aws_lb_listener.https
  ]

  tags = local.tags
}

resource "aws_elasticache_subnet_group" "redis" {
  count = var.enable_elasticache ? 1 : 0

  name       = "${local.project_name}-${var.environment}-redis"
  subnet_ids = [for s in aws_subnet.private : s.id]

  tags = local.tags
}

resource "aws_elasticache_cluster" "redis" {
  count = var.enable_elasticache ? 1 : 0

  cluster_id           = "${local.project_name}-${var.environment}-redis"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.redis[0].name
  security_group_ids   = [aws_security_group.redis[0].id]

  tags = local.tags
}

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.desired_task_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.app]
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${local.project_name}-${var.environment}-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = 120
    scale_out_cooldown = 120
  }
}

