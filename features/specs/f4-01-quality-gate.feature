# SPEC-F4-01, SPEC-F4-02, SPEC-F4-03, SPEC-F4-04 — Frente 4 (T-2.3, issue #9)
#
# Gherkin literal del ticket (issue #9 en GitHub), con el "Then" de UI
# (Settings/Overview) omitido a propósito: esa parte es T-204 (Josue),
# explícitamente "Fuera de Alcance" en el propio issue #9.
Feature: Compuerta de calidad declarativa

  # SPEC-F4-01
  Scenario: cambiar el YAML cambia el resultado sin tocar código
    Given un quality.yaml con min_images_per_class en 300
    And un dataset cuyo min_images_per_class real es 5000
    When se sube el valor a 100000 y se vuelve a correr la compuerta
    Then el check ahora falla
    And no se modificó ningún archivo de código para lograrlo

  # SPEC-F4-02
  Scenario: un fail bloquea de verdad
    Given un check en severidad "fail" que no pasa
    When se ejecuta el pipeline
    Then el proceso termina con exit code distinto de 0

  # SPEC-F4-03
  Scenario: un warn no bloquea pero queda registrado
    Given un check en severidad "warn" que no pasa
    When se ejecuta el pipeline
    Then el proceso continúa
    And el warn aparece en quality.json como un check no cumplido

  # SPEC-F4-04
  Scenario: el reporte trae valor vs umbral
    Given cualquier check evaluado
    Then quality.json incluye resultado, valor observado, umbral y muestras ofensoras
    And no es solo un booleano true/false
