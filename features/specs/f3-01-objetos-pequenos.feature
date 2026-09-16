# SPEC-F3-01 — Frente 3 (T-202, Alejandra)
Feature: Detección de objetos pequeños

  Scenario: umbral configurable, no hardcodeado
    Given un COCO con cajas de distintos tamaños y un umbral de 32x32 en config
    When corre el analizador
    Then reporta % de objetos bajo el umbral, clase más afectada y muestras ofensoras
    And cambiar el umbral en config cambia el resultado sin tocar código
