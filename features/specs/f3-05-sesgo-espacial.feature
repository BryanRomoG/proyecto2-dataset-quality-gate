# SPEC-F3-05 — Frente 3 (T-202, Alejandra)
Feature: Sesgo espacial y estadística descriptiva

  Scenario: distribución sesgada se reporta con más que la media
    Given un conjunto de áreas de cajas con distribución sesgada
    When corre el analizador
    Then reporta media, mediana y percentiles
    And no reporta solo la media cuando la distribución está sesgada
