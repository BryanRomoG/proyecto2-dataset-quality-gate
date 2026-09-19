# SPEC-QA-03 — Regresión de cierre de Fase 3 (issue #16, T-3.5)
#
# Gherkin literal del issue #16: corre el pipeline completo (ingesta ->
# analizadores -> compuerta -> splits -> DVC) de punta a punta sin
# intervención manual, contra el dataset real (T-201..T-201c: 369
# imágenes, car/person, compuerta ya en verde), y confirma que la
# compuerta de Fase 2 sigue bloqueando de verdad con datos de Fase 3
# (splits) encima -- no solo con el COCO plano de Frente 4.
Feature: Regresión de cierre de Fase 3

  Scenario: pipeline completo de punta a punta
    Given el dataset ingresado, analizado, filtrado por la compuerta, particionado y versionado
    When se corre el pipeline completo sin intervención manual
    Then cada etapa produce el output esperado por la siguiente
    And un fail inyectado en un split sigue bloqueando la promoción a PROD
