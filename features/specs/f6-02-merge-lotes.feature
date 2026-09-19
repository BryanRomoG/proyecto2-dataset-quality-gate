# SPEC-F6-06, SPEC-F6-07, SPEC-F6-08, SPEC-F6-09 — Frente 6 (T-3.2b, Alejandra)
Feature: Fusión de lotes de anotación sin colisión de IDs

  Scenario: fusionar dos lotes disjuntos no produce colisión de ids
    Given un dataset base y un lote entrante con ids que se solapan
    When se fusiona el lote entrante sobre el base
    Then ninguna imagen ni anotación del resultado comparte id
    And cada anotación fusionada sigue apuntando a su propia imagen

  Scenario: una categoría con el mismo nombre se reutiliza, no se duplica
    Given un lote entrante con una categoría que existe en el base con otro id numérico
    When se fusiona el lote entrante sobre el base
    Then el dataset resultante tiene una sola categoría con ese nombre

  Scenario: una colisión de nombre de archivo se rechaza con un error claro
    Given un lote entrante con una imagen que usa el mismo file_name que una imagen del base
    When se intenta fusionar el lote entrante sobre el base
    Then la fusión falla nombrando el archivo en colisión

  Scenario: la fusión es reproducible
    Given un dataset base y un lote entrante
    When se fusiona el lote entrante sobre el base dos veces por separado
    Then ambos resultados son idénticos
