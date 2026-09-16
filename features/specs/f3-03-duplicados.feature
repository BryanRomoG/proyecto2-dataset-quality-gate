# SPEC-F3-03 — Frente 3 (T-202, Alejandra)
Feature: Duplicados y near-duplicates por pHash

  Scenario: detecta una copia recomprimida, no solo hash exacto
    Given una imagen del dataset copiada con otro nombre y recomprimida
    When corre el analizador de pHash con umbral de distancia configurable
    Then el par aparece reportado con su similitud
    And un analizador que solo compare MD5/SHA exacto no cumple este escenario
