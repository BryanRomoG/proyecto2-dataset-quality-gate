# SPEC-F5-01, SPEC-F5-02, SPEC-F5-03, SPEC-F5-04 — Frente 5 (T-3.1, Alejandra)
Feature: Splits estratificados sin fuga

  Scenario: todas las clases presentes en val y test
    Given el dataset con ≥300 imágenes por clase
    When se generan los splits con proporciones 0.70/0.15/0.15
    Then las tres particiones suman el total de imágenes
    And todas las clases aparecen en train, val y test

  Scenario: reproducible por semilla
    Given seed=42
    When se corren los splits dos veces
    Then los IDs por split son idénticos (diff vacío)

  Scenario: cero fuga usando los pares de pHash
    Given los pares de near-duplicates detectados en T-202
    When se revisa cada par contra la asignación de split
    Then ambos elementos del par caen en el mismo split
    And la intersección de IDs entre train/val/test es vacía
