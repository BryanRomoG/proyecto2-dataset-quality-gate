# SPEC-F6-01, SPEC-F6-02, SPEC-F6-03, SPEC-F6-04, SPEC-F6-05 — Frente 6 (T-3.2, Alejandra)
Feature: Pipeline DVC reproducible

  Scenario: dvc repro es idempotente
    Given dvc.yaml con etapas declaradas
    When se corre "dvc repro" dos veces seguidas
    Then la segunda corrida no rehace ninguna etapa

  Scenario: solo se rehacen las etapas afectadas
    Given el pipeline ya corrido
    When se modifica un archivo de entrada de una sola etapa
    Then dvc repro solo rehace esa etapa y las que dependen de ella

  Scenario: datos fuera de Git
    Given el repositorio versionado
    Then git ls-files no incluye ningún .jpg/.png/.parquet
    And sí incluye dvc.lock y los archivos .dvc

  @requiere_minio
  Scenario: mismo hash entre DEV y PROD
    Given un dataset empujado a MinIO (dev) y a S3 (prod)
    When se compara el content hash del dvc.lock en ambos remotes
    Then el hash es idéntico
    And ninguna etapa re-empaqueta o re-comprime distinto en PROD
