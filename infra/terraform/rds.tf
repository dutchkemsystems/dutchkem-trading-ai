module "db_africa" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "fortress-db-africa"

  engine               = "postgres"
  engine_version       = "16"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.db_instance_class

  allocated_storage     = 100
  max_allocated_storage = 500

  db_name  = "dutchkem_fortress"
  username = "dutchkem"
  password = var.db_password

  multi_az = true

  db_subnet_group_name   = module.vpc_africa.database_subnet_group_name
  vpc_security_group_ids = [module.vpc_africa.default_security_group_id]

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  performance_insights_enabled = true
  monitoring_interval          = 60

  tags = {
    Region = "africa"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "fortress-redis"
  description          = "Dutchkem Fortress Redis"

  node_type            = "cache.r6g.large"
  num_cache_clusters   = 2
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [module.vpc_africa.default_security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = {
    Region = "africa"
  }
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "fortress-redis"
  subnet_ids = module.vpc_africa.private_subnets
}
