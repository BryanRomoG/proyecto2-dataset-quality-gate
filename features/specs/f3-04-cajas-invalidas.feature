# SPEC-F3-04 — Frente 3 (T-202, Alejandra)
Feature: Cajas inválidas o degeneradas

  Scenario: ancho negativo y caja fuera de imagen se detectan
    Given una caja con width negativo y otra con coordenadas fuera de los límites de la imagen
    When corre el analizador
    Then ambas se reportan como inválidas
    And se valida que area sea coherente con width*height

  Scenario: ancho o alto igual a cero se detectan
    Given una caja con width cero y otra con height cero
    When corre el analizador
    Then ambas se reportan como inválidas
    And cada una indica si el cero fue en el ancho o en el alto
