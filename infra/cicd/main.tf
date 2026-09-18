# ---------------------------------------------------------------------------
# OIDC provider de GitHub Actions — permite que un workflow se autentique
# ante AWS con un token de corta duración (sts:AssumeRoleWithWebIdentity),
# sin llaves de acceso estáticas guardadas en secrets del repo.
# ---------------------------------------------------------------------------
data "tls_certificate" "github_actions" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github_actions.certificates[0].sha1_fingerprint]

  tags = { Name = "${var.project_name}-github-actions-oidc" }
}

# ---------------------------------------------------------------------------
# Rol que asume el workflow de Terraform (solo lectura + fmt/validate/plan).
# Restringido por "sub" a pull_request de este repo exacto: ninguna otra
# rama, repo o tipo de evento puede asumirlo aunque conozca el ARN.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "github_actions_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}/${var.github_repo}:pull_request"]
    }
  }
}

resource "aws_iam_role" "github_actions_terraform_plan" {
  name               = "${var.project_name}-gha-terraform-plan"
  assume_role_policy = data.aws_iam_policy_document.github_actions_trust.json

  tags = { Name = "${var.project_name}-gha-terraform-plan" }
}

# Permite leer/lockear el bucket de remote state (terraform init/plan
# necesita GetObject + PutObject para el locking nativo de S3, aunque el
# plan en sí sea de solo lectura sobre los recursos de AWS).
data "aws_iam_policy_document" "terraform_state_access" {
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.state_bucket_name}"]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.state_bucket_name}/*"]
  }
}

resource "aws_iam_role_policy" "terraform_state_access" {
  name   = "terraform-state-access"
  role   = aws_iam_role.github_actions_terraform_plan.id
  policy = data.aws_iam_policy_document.terraform_state_access.json
}

# Permisos de solo lectura sobre los recursos reales (VPC, RDS, S3, ECS,
# ECR, IAM, etc.) — suficiente para que "terraform plan" pueda diffear el
# estado real contra el código sin poder modificar nada.
resource "aws_iam_role_policy_attachment" "read_only" {
  role       = aws_iam_role.github_actions_terraform_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}
