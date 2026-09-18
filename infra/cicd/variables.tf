variable "project_name" {
  type    = string
  default = "dataset-quality-gate"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "github_org" {
  description = "Organización o usuario de GitHub dueño del repo (ej. \"BryanRomoG\")."
  type        = string
}

variable "github_repo" {
  description = "Nombre del repo, sin el org (ej. \"proyecto2-dataset-quality-gate\")."
  type        = string
}

variable "state_bucket_name" {
  description = "Bucket S3 de remote state creado por infra/bootstrap — el rol de CI necesita leer/lockear ahí para poder correr terraform plan en cada capa."
  type        = string
}
