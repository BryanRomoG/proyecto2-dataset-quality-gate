data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = var.network_state_bucket
    key    = var.network_state_key
    region = var.aws_region
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ---------------------------------------------------------------------------
# Credenciales — nunca hardcodeadas. Se generan en el apply y se guardan
# en Secrets Manager; la app las lee en runtime desde ahí, no desde .tf
# ni desde variables de entorno versionadas.
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 32
  special = false # evita caracteres que MariaDB/librerías de conexión escapan mal
}

resource "aws_secretsmanager_secret" "db" {
  name = "${local.name_prefix}/mariadb"
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id

  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    dbname   = var.db_name
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
  })
}

# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  tags = { Name = "${local.name_prefix}-db-subnets" }
}

resource "aws_security_group" "db" {
  name_prefix = "${local.name_prefix}-db-"
  description = "MariaDB: acceso solo desde dentro de la VPC (subredes privadas)."
  vpc_id      = data.terraform_remote_state.network.outputs.vpc_id

  ingress {
    description = "MariaDB desde la VPC. TODO: acotar a la SG de compute cuando esa capa exista, en vez del CIDR completo."
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [data.terraform_remote_state.network.outputs.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-db-sg" }
}

# ---------------------------------------------------------------------------
# RDS (MariaDB) — equivalente productivo del contenedor mariadb de
# docker-compose en dev/local.
# ---------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier     = "${local.name_prefix}-db"
  engine         = "mariadb"
  engine_version = "10.11"

  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_encrypted      = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  multi_az                = var.environment == "prod"
  backup_retention_period = var.environment == "prod" ? 7 : 1
  skip_final_snapshot     = var.environment != "prod"
  deletion_protection     = var.environment == "prod"
  publicly_accessible     = false

  tags = { Name = "${local.name_prefix}-db" }
}
