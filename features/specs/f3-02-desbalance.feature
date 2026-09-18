# SPEC-F3-02 — Frente 3 (T-202, Alejandra)
Feature: Desbalance de clases

  Scenario: ratio mayoría/minoría correcto
    Given conteos de imágenes por clase
    When corre el analizador
    Then reporta el ratio clase mayoritaria / minoritaria
    And lista las clases por debajo del mínimo configurado
