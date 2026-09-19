output "github_actions_role_arn" {
  description = "Copiar a la variable de repo AWS_TERRAFORM_PLAN_ROLE_ARN en GitHub (Settings > Secrets and variables > Actions > Variables)."
  value       = aws_iam_role.github_actions_terraform_plan.arn
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github_actions.arn
}
