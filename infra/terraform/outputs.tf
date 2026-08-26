output "africa_cluster_endpoint" {
  value = module.eks_africa.cluster_endpoint
}

output "africa_cluster_name" {
  value = module.eks_africa.cluster_name
}

output "africa_db_endpoint" {
  value = module.db_africa.db_instance_endpoint
  sensitive = true
}

output "africa_vpc_id" {
  value = module.vpc_africa.vpc_id
}

output "africa_redis_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "europe_vpc_id" {
  value = module.vpc_europe.vpc_id
}
