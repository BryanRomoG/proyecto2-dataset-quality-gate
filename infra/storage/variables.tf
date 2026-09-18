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
  description = "Bucket S3 donde vive el remote state de la capa network (mismo bucket de backend, distinta key)."
  type        = string
}

variable "network_state_key" {
  description = "Key del state de network dentro del bucket."
  type        = string
  default     = "network/terraform.tfstate"
}
