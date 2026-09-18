# ---------------------------------------------------------------------------
# BOOTSTRAP — se corre UNA sola vez, antes que cualquier otra capa.
#
# Este es el único módulo del proyecto con backend local ("terraform.tfstate"
# en disco). Es intencional: no puede apuntar a un backend remoto en S3
# porque este módulo es justamente el que CREA ese bucket S3 (problema del
# huevo y la gallina). Su .tfstate local se guarda fuera del repo (ver
# .gitignore) y solo lo corre quien haga el setup inicial de infraestructura.
#
# Uso:
#   cd infra/bootstrap
#   terraform init
#   terraform apply -var="project_name=dataset-quality-gate" -var="environment=dev"
#   # copiar el output state_bucket_name a infra/backend.hcl
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  bucket_name = "${var.project_name}-${var.environment}-tfstate"
}

resource "aws_s3_bucket" "state" {
  bucket = local.bucket_name

  # Evita borrar el bucket de state por accidente con un terraform destroy.
  lifecycle {
    prevent_destroy = true
  }

  tags = { Name = local.bucket_name }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Terraform >= 1.10 soporta locking nativo en S3 (use_lockfile = true en el
# backend), sin necesitar una tabla DynamoDB aparte. Si el equipo usa una
# versión anterior, agregar aquí un aws_dynamodb_table con hash_key
# "LockID" y referenciarla como dynamodb_table en cada backend.hcl.
