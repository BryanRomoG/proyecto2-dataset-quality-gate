# SPEC-F10-02 — Frente 10 (T-4.2, issue #18)
#
# Prueba de mutación manual: romper deliberadamente lógica crítica y
# confirmar que la suite realmente lo detecta, igual que hará el
# evaluador el día de la entrega ("invertir el comparador lógico de la
# compuerta y confirmar que pytest pasa a rojo; restaurar después").
Feature: Prueba de mutación manual

  Scenario: invertir el comparador de la compuerta rompe la suite
    Given la compuerta de calidad con su comparador correcto
    When se invierte el comparador deliberadamente
    Then pytest pasa a rojo
    And el código se restaura después de la prueba

  Scenario: romper el cálculo de área de las cajas rompe la suite
    Given el cálculo de area = width * height
    When se rompe deliberadamente
    Then los tests relacionados fallan
    And se restaura el código original
