# SPEC-F2-01, SPEC-F2-02, SPEC-F2-03 — Frente 2 (T-1.3, Alejandra)
Feature: Validación estricta del COCO de entrada
  Como pipeline de ingesta
  Quiero rechazar COCO malformado con un error específico
  Para no propagar datos corruptos a los analizadores

  # SPEC-F2-01
  Scenario: bbox con longitud incorrecta se rechaza nombrando el campo
    Given un JSON COCO con una anotación cuyo bbox tiene 3 elementos
    When se valida con el modelo Pydantic de Annotation
    Then la validación falla
    And el error nombra el campo "bbox", no lanza un traceback crudo

  # SPEC-F2-01
  Scenario: category_id inexistente se rechaza
    Given una anotación con category_id que no existe en categories
    When se valida el COCO completo
    Then la validación falla nombrando "category_id"

  # SPEC-F2-01
  Scenario: image_id huérfano se rechaza
    Given una anotación cuyo image_id no aparece en images
    When se valida el COCO completo
    Then la validación falla nombrando "image_id"

  # SPEC-F2-02
  Scenario: configuración de entorno inválida falla rápido
    Given un .env sin UPLOAD_MAX_BYTES o con un valor no numérico
    When arranca la aplicación
    Then falla al inicio con un mensaje claro
    And no falla más adelante de forma confusa a mitad de un analizador
