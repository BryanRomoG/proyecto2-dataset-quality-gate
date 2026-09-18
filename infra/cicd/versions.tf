# ---------------------------------------------------------------------------
# CICD — igual que bootstrap/, se corre UNA sola vez y a mano por quien tenga
# acceso admin a la cuenta de AWS. Backend local a propósito: crea el propio
# rol IAM que GitHub Actions necesita para autenticarse, así que no puede
# depender de que ese rol ya exista para leer su remote state.
#
# Uso:
#   cd infra/cicd
#   terraform init
#   terraform apply \
#     -var="github_org=BryanRomoG" \
#     -var="github_repo=proyecto2-dataset-quality-gate" \
#     -var="state_bucket_name=<state_bucket_name del bootstrap>"
#   # copiar el output github_actions_role_arn a las variables/secrets del
#   # repo en GitHub (ver infra/README.md)
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
