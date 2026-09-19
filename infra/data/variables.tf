variable "project_name" {
  type    = string
  default = "dataset-quality-gate"
}

variable "environment" {
  type    = string
  default = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment debe ser \"dev\" o \"prod\"."
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "network_state_bucket" {
  type = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.network_state_bucket))
    error_message = "network_state_bucket debe ser el nombre real del bucket de state (minúsculas, 3-63 caracteres), no un placeholder."
  }
}

variable "network_state_key" {
  type    = string
  default = "network/terraform.tfstate"
}

variable "db_name" {
  type    = string
  default = "dataset_quality_gate"
}

variable "db_username" {
  description = "Usuario administrador de MariaDB. La contraseña NUNCA se define aquí: se genera con random_password y se guarda en Secrets Manager (ver main.tf)."
  type        = string
  default     = "app_admin"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
