variable "project_name" {
  description = "Nombre corto del proyecto, usado como prefijo de recursos."
  type        = string
  default     = "dataset-quality-gate"
}

variable "environment" {
  description = "Entorno de despliegue (dev | prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment debe ser \"dev\" o \"prod\"."
  }
}

variable "aws_region" {
  description = "Región de AWS donde se despliega la infraestructura."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "Bloque CIDR de la VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Número de zonas de disponibilidad a usar (subredes pública/privada por AZ)."
  type        = number
  default     = 2
}
