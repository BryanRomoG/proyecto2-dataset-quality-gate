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
}

variable "network_state_key" {
  type    = string
  default = "network/terraform.tfstate"
}

variable "data_state_key" {
  type    = string
  default = "data/terraform.tfstate"
}

variable "container_port" {
  description = "Puerto que expone el monolito Express dentro del contenedor (mismo que PORT en .env)."
  type        = number
  default     = 3100
}

variable "task_cpu" {
  type    = string
  default = "512"
}

variable "task_memory" {
  type    = string
  default = "1024"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "container_image" {
  description = "Imagen a desplegar. Por defecto apunta al ECR repo creado en esta misma capa con tag :latest; CI/CD la sobreescribe con el digest real en cada deploy."
  type        = string
  default     = ""
}
