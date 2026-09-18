output "db_endpoint" {
  value = aws_db_instance.main.address
}

output "db_security_group_id" {
  value = aws_security_group.db.id
}

output "db_secret_arn" {
  description = "ARN del secreto en Secrets Manager con host/usuario/password/dbname."
  value       = aws_secretsmanager_secret.db.arn
}
