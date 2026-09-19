output "vpc_id" {
  value = aws_vpc.main.id
}

output "vpc_cidr" {
  value = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "s3_vpc_endpoint_id" {
  description = "Usado por la capa storage para restringir el bucket policy al tráfico que entra por este endpoint."
  value       = aws_vpc_endpoint.s3.id
}

output "private_route_table_ids" {
  value = [aws_route_table.private.id]
}
