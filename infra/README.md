# Infraestructura como código — Frente 9 (T-304)

Terraform por capas: `network` → `data` → `storage` → `compute`. Cada capa
tiene su propio state remoto en S3 (nunca `.tfstate` local, excepto
`bootstrap/`, ver más abajo) y se referencian entre sí vía
`terraform_remote_state`, no copiando valores a mano.

## Orden de aplicación

1. **`bootstrap/`** — una sola vez, crea el bucket S3 de remote state.
   Backend local a propósito (huevo y gallina): no puede vivir en el S3
   que él mismo crea.
2. **`network/`** — VPC, subredes públicas/privadas, NAT, VPC endpoint de
   S3 (Gateway).
3. **`data/`** — RDS MariaDB, credenciales en Secrets Manager (nunca en
   `.tf` ni hardcodeadas).
4. **`storage/`** — bucket S3 del dataset, con policy restringida al VPC
   endpoint creado en `network/`.
5. **`compute/`** — ECS Fargate + ALB + ECR, lee el secreto de `data/` por
   ARN (no por valor) y lo inyecta como variable de entorno segura en la
   task definition.

## Setup inicial

```bash
# 1) Bootstrap (una sola vez)
cd infra/bootstrap
terraform init
terraform apply -var="project_name=dataset-quality-gate" -var="environment=dev"
# copiar el output state_bucket_name

# 2) En cada capa restante: copiar la plantilla de backend y ajustar
cp infra/backend.hcl.example infra/network/backend.hcl
cp infra/backend.hcl.example infra/data/backend.hcl
cp infra/backend.hcl.example infra/storage/backend.hcl
cp infra/backend.hcl.example infra/compute/backend.hcl
# editar cada backend.hcl: bucket = "<state_bucket_name del paso 1>"

# 3) Aplicar en orden
cd infra/network  && terraform init -backend-config=backend.hcl && terraform apply
cd infra/data     && terraform init -backend-config=backend.hcl \
                     -var="network_state_bucket=<state_bucket_name>" && terraform apply
cd infra/storage  && terraform init -backend-config=backend.hcl \
                     -var="network_state_bucket=<state_bucket_name>" && terraform apply
cd infra/compute  && terraform init -backend-config=backend.hcl \
                     -var="network_state_bucket=<state_bucket_name>" && terraform apply
```

`network_state_bucket` es el mismo bucket para las cuatro capas (solo
cambia la `key` dentro de él); por eso también se pasa como variable a
`data`, `storage` y `compute`, que lo usan para leer el remote state de
`network` (y `compute` además lee el de `data`).

## Verificación (control de T-304)

Corre esto en cada carpeta de capa antes de dar por cerrado el ticket:

```bash
terraform fmt -recursive
terraform validate
terraform plan
```

Las tres deben salir en verde. `fmt -recursive` desde `infra/` formatea
las cuatro capas y el bootstrap de una sola vez.

## Cero secretos hardcodeados

- La contraseña de MariaDB se genera con `random_password` en `data/` y se
  guarda en Secrets Manager — no aparece en ningún `.tf`, ni en
  `terraform.tfstate` en texto plano más de lo que AWS ya cifra en reposo
  (bucket con `sse-s3` habilitado).
- `compute/` inyecta el secreto a la tarea ECS por **ARN** (`valueFrom`),
  no por valor: el contenido nunca pasa por la definición de la task ni
  por logs de `terraform plan`.
- `backend.hcl` (con el nombre real del bucket de state) está en
  `.gitignore` — solo se commitea `backend.hcl.example`.

## Pendiente / a decidir con el equipo

- La SG de `data/` acepta el CIDR completo de la VPC en el puerto 3306 en
  vez de acotarse a la SG de `compute/`, porque `data/` se aplica antes
  que `compute/` y crear la dependencia inversa generaría un ciclo entre
  capas. Si el equipo prefiere cerrarlo más, la alternativa es fusionar
  `data` y `compute` en una sola capa o añadir una regla de SG por
  separado después de que ambas existan.
- `container_image` en `compute/` apunta a `:latest` del ECR creado en la
  misma capa por defecto; el pipeline de CI/CD (fuera del alcance de
  T-304) debería sobreescribirlo con el digest inmutable de cada build.
