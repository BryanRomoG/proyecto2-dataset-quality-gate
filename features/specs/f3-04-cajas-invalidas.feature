# SPEC-F3-04 — Frente 3 (T-202, Alejandra)
Feature: Cajas inválidas o degeneradas

  Scenario: ancho negativo y caja fuera de imagen se detectan
    Given una caja con width negativo y otra con coordenadas fuera de los límites de la imagen
    When corre el analizador
    Then ambas se reportan como inválidas
    And se valida que area sea coherente con width*height
