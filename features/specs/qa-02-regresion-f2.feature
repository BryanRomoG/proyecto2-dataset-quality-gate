# SPEC-QA-02 — Regresión de cierre de Fase 2 (issue #11, T-2.5)
#
# Gherkin literal del issue #11: confirma que Fase 1 (ingesta Pydantic,
# T-1.3) sigue sana con Fase 2 (analizadores del Frente 3 + compuerta del
# Frente 4) encima, y que quality.yaml con el umbral real del curso no
# rompe la ingesta. Se ejecuta después de tener dataset real (T-201..T-204)
# porque antes no había con qué probar esto de forma honesta.
Feature: Regresión de cierre de Fase 2

  Scenario: Fase 1 sigue sana con Fase 2 encima
    Given la suite completa de Fase 1 (docker, Pydantic) y Fase 2 (analizadores, compuerta)
    When se corren juntas en CI
    Then ambas terminan en verde en la misma corrida

  Scenario: quality.yaml con el umbral real del curso no rompe la ingesta
    Given un dataset COCO válido y quality.yaml con min_images_per_class en 300
    When se valida el dataset (T-103, ingesta)
    Then la validación pasa sin importar el resultado de la compuerta
