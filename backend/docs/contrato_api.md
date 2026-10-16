# Contrato de la API - Hackathon Expo Clean 2026

Este documento define las estructuras JSON exactas que usarán el Frontend y el Backend para comunicarse. 

```json
{
  "id": "borr-1234",
  "cliente_id": "cli-999",
  "periodo": "Mensual",
  "estado": "borrador",
  "grupos": [
    {
      "id": "grp-001",
      "nombre": "Oficinas Principales",
      "cantidad": 1,
      "superficie_fisica": 150.0,
      "dias_semanales": 5,
      "visitas_diarias": 1,
      "estado_confirmacion": "confirmado",
      "trabajos": [
        {
          "tipo": "general",
          "superficie_usada": 150.0,
          "horas_estimadas": 4.5,
          "personas": 1
        }
      ],
      "recursos": [
        {
          "tipo": "propio",
          "id_insumo": 101,
          "cantidad": 2.5,
          "costo_unitario": 18.50
        }
      ]
    }
  ]
}