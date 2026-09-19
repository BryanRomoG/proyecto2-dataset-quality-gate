# Infraestructura como código — Frente 9 (T-304)

Terraform por capas: `network` → `data` → `storage` → `compute`. Cada capa
tiene su propio state remoto en S3 (nunca `.tfstate` local, excepto
`bootstrap/` y `cicd/`, ver más abajo) y se referencian entre sí vía
`terraform_remote_state`, no copiando valores a mano.

## Orden de aplicación

1. **`bootstrap/`** — una sola vez, crea el bucket S3 de remote state.
   Backend local a propósito (huevo y gallina): no puede vivir en el S3
   que él mismo crea.
2. **`cicd/`** — una sola vez, crea el OIDC provider de GitHub Actions y el
   rol IAM de solo lectura que usa el workflow de CI (ver sección
   "GitHub Actions (OIDC, sin llaves estáticas)" más abajo). También
   backend local, por la misma razón que `bootstrap/`.
3. **`network/`** — VPC, subredes públicas/privadas, NAT, VPC endpoint de
   S3 (Gateway).
4. **`data/`** — RDS MariaDB, credenciales en Secrets Manager (nunca en
   `.tf` ni hardcodeadas).
5. **`storage/`** — bucket S3 del dataset, con policy restringida al VPC
   endpoint creado en `network/`.
6. **`compute/`** — ECS Fargate + ALB + ECR, lee el secreto de `data/` por
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

## GitHub Actions (OIDC, sin llaves estáticas)

`.github/workflows/terraform.yml` corre `fmt -check`, `validate` y `plan`
(solo lectura, nunca `apply`) en cada PR que toque `infra/`. Se autentica
con AWS mediante OIDC (`aws-actions/configure-aws-credentials` +
`role-to-assume`), **nunca** con `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
guardadas como secret — así lo pidió la revisión de seguridad.

Setup (una sola vez, requiere acceso admin a la cuenta de AWS):

```bash
cd infra/cicd
terraform init
terraform apply \
  -var="github_org=BryanRomoG" \
  -var="github_repo=proyecto2-dataset-quality-gate" \
  -var="state_bucket_name=dataset-quality-gate-dev-tfstate"
```

`state_bucket_name` tiene que ser el nombre **real** del bucket (el output
de `infra/bootstrap`), no el placeholder: ese string se incrusta literal en
el ARN de la policy del rol, así que un valor equivocado deja al rol sin
permiso sobre el bucket de verdad y el error solo aparece después, como
`AccessDenied` al `s3:PutObject` del `.tflock` en el `terraform plan` de CI.
La variable valida el formato para atajar ese caso.

Con el output `github_actions_role_arn`, en GitHub ir a
**Settings → Secrets and variables → Actions → Variables** (no "Secrets":
un ARN de rol y un nombre de bucket no son secretos, y así quedan
disponibles para PRs desde forks igual que para el mismo repo) y crear:

- `AWS_TERRAFORM_PLAN_ROLE_ARN` = el output `github_actions_role_arn`.
- `TF_STATE_BUCKET` = el mismo bucket que devolvió `bootstrap` (el de
  `state_bucket_name`).

El rol (`infra/cicd/main.tf`) queda restringido a:
- Confianza (`assume_role_policy`): solo `token.actions.githubusercontent.com`
  con `aud = sts.amazonaws.com` y un `sub` de la lista exacta en
  `local.github_actions_subs` — ningún otro repo, rama o tipo de evento puede
  asumirlo aunque conozca el ARN. Son dos valores porque GitHub emite el `sub`
  con los IDs numéricos inmutables del owner y del repo
  (`repo:BryanRomoG@178322887/proyecto2-dataset-quality-gate@1366771913:pull_request`)
  y se acepta también el formato viejo sin IDs.

> **No edites esta trust policy a mano en la consola de AWS.** Terraform es el
> dueño del recurso: el siguiente `apply` revierte el cambio y CI se rompe con
> `Not authorized to perform sts:AssumeRoleWithWebIdentity`. Si el `sub` real
> cambia, ajústalo en `infra/cicd/main.tf` y aplica. Para ver el `sub` que
> emite GitHub, el workflow tiene un paso `Debug OIDC token claims` en el job
> `plan (network)`.
- Permisos: `ReadOnlyAccess` (managed policy de AWS) más lectura/lock del
  bucket de state — suficiente para `terraform plan`, insuficiente para
  crear, modificar o borrar nada. El `apply` real sigue siendo manual,
  desde la máquina de quien tenga las credenciales de administración
  (ver "Setup inicial" arriba).

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
