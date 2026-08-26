module "eks_africa" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.cluster_name}-africa"
  cluster_version = "1.29"

  vpc_id     = module.vpc_africa.vpc_id
  subnet_ids = module.vpc_africa.private_subnets

  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    general = {
      min_size     = 2
      max_size     = 10
      desired_size = 3

      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"
    }

    compute = {
      min_size     = 1
      max_size     = 5
      desired_size = 2

      instance_types = ["c6g.xlarge"]
      capacity_type  = "ON_DEMAND"
    }
  }

  tags = {
    Region = "africa"
  }
}
