# Lee los outputs de la capa "network" (VPC endpoint id) para no duplicar
# ese dato ni acoplar los layers por variables manuales.
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = var.network_state_bucket
    key    = var.network_state_key
    region = var.aws_region
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  bucket_name = "${local.name_prefix}-dataset"
}

resource "aws_s3_bucket" "dataset" {
  bucket = local.bucket_name

  tags = { Name = local.bucket_name }
}

resource "aws_s3_bucket_versioning" "dataset" {
  bucket = aws_s3_bucket.dataset.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dataset" {
  bucket = aws_s3_bucket.dataset.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "dataset" {
  bucket = aws_s3_bucket.dataset.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Solo se puede llegar al bucket vía el VPC endpoint de la capa network,
# o vía la consola/CLI con credenciales de administración (no forzado aquí
# a propósito, para no bloquear a Bryan/PM en tareas de auditoría manual).
resource "aws_s3_bucket_policy" "dataset_vpc_only" {
  bucket = aws_s3_bucket.dataset.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyIfNotFromVpcEndpoint"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.dataset.arn,
          "${aws_s3_bucket.dataset.arn}/*",
        ]
        Condition = {
          StringNotEquals = {
            "aws:sourceVpce" = data.terraform_remote_state.network.outputs.s3_vpc_endpoint_id
          }
          # Excepción: permite acceso fuera de la VPC solo si viene con el
          # rol/usuario de administración del proyecto (bootstrap, CI/CD,
          # auditoría manual desde fuera de AWS).
          StringNotLike = {
            "aws:PrincipalArn" = "arn:aws:iam::*:role/${var.project_name}-admin"
          }
        }
      }
    ]
  })
}
