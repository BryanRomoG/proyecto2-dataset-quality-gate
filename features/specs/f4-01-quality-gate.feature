# SPEC-F4-01, SPEC-F4-02 — Frente 4 (T-203, Juan Pablo)
Feature: Compuerta de calidad del dataset
  Como pipeline de calidad
  Quiero bloquear el release cuando una métrica crítica no cumple su umbral
  Para que un dataset insuficiente nunca se libere en silencio

  # SPEC-F4-01
  Scenario: un check "fail" que no cumple bloquea la compuerta
    Given un quality.yaml con min_images_per_class en 300 y severidad "fail"
    And un dataset cuyo min_images_per_class real es 250
    When se corre la compuerta
    Then el reporte queda marcado como no aprobado
    And el proceso termina con un código de salida distinto de cero

  # SPEC-F4-01
  Scenario: un check "fail" que sí cumple deja pasar la compuerta
    Given un quality.yaml con min_images_per_class en 300 y severidad "fail"
    And un dataset cuyo min_images_per_class real es 300
    When se corre la compuerta
    Then el reporte queda marcado como aprobado
    And el proceso termina con código de salida 0

  # SPEC-F4-02
  Scenario: un check "warn" que no cumple no bloquea la compuerta
    Given un quality.yaml con min_images_per_class en 300 y severidad "warn"
    And un dataset cuyo min_images_per_class real es 250
    When se corre la compuerta
    Then el check individual queda marcado como no cumplido
    But el reporte queda marcado como aprobado

  # SPEC-F4-01 (T-203, verificación de Control 2)
  Scenario: subir el umbral a un valor imposible bloquea incluso un dataset saludable
    Given un dataset cuyo min_images_per_class real es 5000
    And un quality.yaml con min_images_per_class en 99999 y severidad "fail"
    When se corre la compuerta
    Then el proceso termina con un código de salida distinto de cero
