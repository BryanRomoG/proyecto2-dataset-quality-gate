# Checklist de requisitos mínimos — PM

Verificación de M1/M2/M3 según el prompt de evaluación, a cargo del PM (Bryan), independiente de la evidencia que el equipo va generando en cada PR.

## M1 — Arranque desde clon limpio

- [x] Clonado en máquina distinta a la de quien escribió el docker-compose
- [x] `cp .env.example .env` sin editar nada a mano
- [x] `docker compose up --build` levanta app + MariaDB + MinIO
- [x] `/api/health` responde OK
- [ ] Pipeline de Python (analizadores/compuerta) integrado al arranque — **pendiente**, ver Dockerfile

## M2 — Sin secretos versionados

- [x] `.env.example` existe con placeholders, sin valores reales
- [x] `.env` real está en `.gitignore`
- [x] Revisado `git log --all -p` en busca de `AKIA`, `AWS_SECRET_ACCESS_KEY`, `*_API_KEY` — sin coincidencias

## M3 — Volumen de anotación (≥300 imágenes/clase en ≥2 clases)

- [x] Conteo verificado sobre el COCO entregado (no sobre lo que dice el README)
- [x] Conteo repetido después de colapsar near-duplicates (pHash) — sin cambio
- [x] Clases que cumplen: `car`, `person`

## Notas

Este checklist se actualiza en cada Control (1, 2, 3) antes de solicitar re-evaluación.