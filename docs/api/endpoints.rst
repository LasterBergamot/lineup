API Endpoints
=============

This page documents all available API endpoints.

Health Check
------------

Check API Health
^^^^^^^^^^^^^^^^

Returns the current health status of the API.

.. http:get:: /api/v1/health

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:5000/api/v1/health

   **Example Response:**

   .. code-block:: json

      {
          "status": "healthy",
          "timestamp": "2026-01-10T12:00:00.000000"
      }

   :statuscode 200: API is healthy

Lineup Endpoints
----------------

.. note::
   Lineup endpoints are planned for Phase 2 of development.

The following endpoints are planned:

Create Lineup
^^^^^^^^^^^^^

.. http:post:: /api/v1/lineups

   Create a new lineup for a match.

   **Request Body:**

   .. code-block:: json

      {
          "match_id": "uuid",
          "team_id": "uuid",
          "sport": "water_polo",
          "players": [
              {
                  "player_id": "uuid",
                  "position": "goalkeeper",
                  "number": 1
              }
          ]
      }

   **Response:**

   .. code-block:: json

      {
          "status": "success",
          "data": {
              "lineup_id": "uuid",
              "match_id": "uuid",
              "team_id": "uuid",
              "created_at": "2026-01-10T12:00:00.000000"
          }
      }

   :statuscode 201: Lineup created successfully
   :statuscode 400: Invalid request data
   :statuscode 422: Validation error

Get Lineup
^^^^^^^^^^

.. http:get:: /api/v1/lineups/(uuid:lineup_id)

   Retrieve a specific lineup.

   :param lineup_id: The UUID of the lineup

   **Example Response:**

   .. code-block:: json

      {
          "status": "success",
          "data": {
              "lineup_id": "uuid",
              "match_id": "uuid",
              "team_id": "uuid",
              "sport": "water_polo",
              "players": [],
              "created_at": "2026-01-10T12:00:00.000000",
              "updated_at": "2026-01-10T12:00:00.000000"
          }
      }

   :statuscode 200: Lineup retrieved successfully
   :statuscode 404: Lineup not found

Update Lineup
^^^^^^^^^^^^^

.. http:put:: /api/v1/lineups/(uuid:lineup_id)

   Update an existing lineup.

   :param lineup_id: The UUID of the lineup

   **Request Body:** Same as Create Lineup

   :statuscode 200: Lineup updated successfully
   :statuscode 400: Invalid request data
   :statuscode 404: Lineup not found
   :statuscode 422: Validation error

Delete Lineup
^^^^^^^^^^^^^

.. http:delete:: /api/v1/lineups/(uuid:lineup_id)

   Delete a lineup.

   :param lineup_id: The UUID of the lineup

   :statuscode 204: Lineup deleted successfully
   :statuscode 404: Lineup not found

Export Lineup to PDF
^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/v1/lineups/(uuid:lineup_id)/pdf

   Export a lineup to PDF format (Rajtlista for water polo).

   :param lineup_id: The UUID of the lineup

   :statuscode 200: PDF generated successfully
   :statuscode 404: Lineup not found
   :statuscode 500: PDF generation error

Team Endpoints
--------------

.. note::
   Team management endpoints are planned for Phase 3 of development.

Player Endpoints
----------------

.. note::
   Player management endpoints are planned for Phase 3 of development.

Match Endpoints
---------------

.. note::
   Match management endpoints are planned for Phase 3 of development.
