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

# GitHub emite el claim "sub" con los IDs numéricos inmutables del owner y del
# repo (repo:owner@<id>/repo@<id>:<evento>). Son inmutables a propósito: si
# alguien renombra el usuario o el repo, o borra la cuenta y otro reclama el
# nombre, el ID no se reutiliza y la trust policy no se puede secuestrar.
# Obtenerlos con:  gh api repos/BryanRomoG/proyecto2-dataset-quality-gate --jq '{repo: .id, owner: .owner.id}'
variable "github_org_id" {
  description = "ID numérico del owner del repo en GitHub."
  type        = string
  default     = "178322887"
}

variable "github_repo_id" {
  description = "ID numérico del repo en GitHub."
  type        = string
  default     = "1366771913"
}

variable "state_bucket_name" {
  description = "Bucket S3 de remote state creado por infra/bootstrap — el rol de CI necesita leer/lockear ahí para poder correr terraform plan en cada capa."
  type        = string

  # Este valor se incrusta literal en el ARN de la policy del rol. Si entra un
  # placeholder ("<state_bucket_name del bootstrap>"), el apply pasa sin ruido
  # y el permiso queda apuntando a un bucket que no existe; el fallo reaparece
  # mucho después como un AccessDenied en el terraform plan de CI.
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "state_bucket_name debe ser el nombre real del bucket (minúsculas, 3-63 caracteres), no un placeholder: usa el output state_bucket_name de infra/bootstrap."
  }
}
