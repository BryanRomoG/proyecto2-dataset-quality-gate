terraform {
  # >= 1.10: el backend S3 de abajo se inicializa con use_lockfile=true
  # (locking nativo en S3, sin tabla DynamoDB), soportado desde 1.10.
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend parcial: el bucket/tabla de lock se pasan con -backend-config
  # (ver infra/backend.hcl.example). Nunca se hardcodea aquí para poder
  # reutilizar el mismo código entre DEV y PROD con distintos state files.
  backend "s3" {
    key     = "network/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Layer       = "network"
    }
  }
}
