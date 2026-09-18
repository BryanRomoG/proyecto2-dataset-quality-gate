# SPEC-F10-01, SPEC-F10-04, SPEC-F11-03 — Frente 10/11 (T-4.3, issue #19)
Feature: CI que falla de verdad

  # SPEC-F10-04
  Scenario: un commit que rompe algo tumba el build
    Given un commit que rompe un test o el lint
    When corre el workflow de GitHub Actions
    Then el build termina en rojo
    And ningún paso usa continue-on-error para maquillar el resultado

  # SPEC-F11-03
  Scenario: .gitignore correcto
    Given git ls-files
    Then no aparece ningún .env, __pycache__, .venv, .dvc/cache, .tfstate ni node_modules
