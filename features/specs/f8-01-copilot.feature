# SPEC-F8-01 a SPEC-F8-06 — Frente 8, Dataset Copilot (T-3.3, issue #14)
#
# El Gherkin literal del issue agrupa "cita versión" y "manejo de errores"
# en una sola línea; aquí se separan en dos escenarios (SPEC-F8-05 y
# SPEC-F8-06) porque la propia rúbrica del ticket los puntúa por separado
# (2 pts cita versión + 1 pt manejo de errores) y son dos comportamientos
# independientes de probar.
Feature: Dataset Copilot (servidor MCP de solo lectura)

  # SPEC-F8-01
  Scenario: ninguna herramienta tiene efectos de escritura
    Given el Copilot con sus cuatro herramientas de solo lectura
    When se invoca cada herramienta disponible
    Then ningún archivo de datos cambió
    And el código de las herramientas no contiene ningún patrón de escritura

  # SPEC-F8-02
  Scenario: una respuesta con cifras trae la traza completa de tool calls
    Given una pregunta que el LLM solo puede responder usando una herramienta
    When el Copilot responde
    Then la respuesta trae al menos una llamada a herramienta en su traza
    And la traza incluye el nombre de la herramienta y el resultado que devolvió

  # SPEC-F8-03
  Scenario: la respuesta cambia si cambia la fuente de datos
    Given dos fuentes de datos con reportes de calidad distintos
    When se hace la misma pregunta contra cada una
    Then las dos respuestas citan cifras distintas

  # SPEC-F8-04
  Scenario: el Copilot admite no saber en vez de inventar una cifra
    Given una pregunta que ninguna herramienta puede responder
    When el Copilot responde
    Then la respuesta admite que no lo sabe
    And no se llamó a ninguna herramienta
    And no cita ninguna versión de dataset

  # SPEC-F8-05
  Scenario: cada respuesta que usó herramientas cita la versión del dataset
    Given una pregunta que el LLM solo puede responder usando una herramienta
    When el Copilot responde
    Then la respuesta cita la versión actual del dataset

  # SPEC-F8-06
  Scenario: un error del LLM se maneja sin traceback
    Given un LLM que no responde
    When el Copilot responde
    Then la respuesta trae un mensaje de error manejado
    And el mensaje de error no contiene un traceback de Python
