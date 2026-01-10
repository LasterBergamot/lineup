API Reference
=============

This section provides detailed documentation of the Lineup API endpoints and modules.

.. toctree::
   :maxdepth: 2

   endpoints
   modules

API Overview
------------

The Lineup API is a RESTful API that provides endpoints for managing sports team lineups.

Base URL
^^^^^^^^

Local Development:

.. code-block:: text

   http://localhost:5000/api/v1

Production:

.. code-block:: text

   https://api.lineup.example.com/api/v1

Authentication
--------------

.. note::
   Authentication is planned for Phase 5 of development. Currently, the API is open for development purposes.

Future authentication will use:

* **JWT tokens** for API authentication
* **OAuth 2.0** for user authentication (Google accounts)

Response Format
---------------

All API responses are in JSON format.

Success Response
^^^^^^^^^^^^^^^^

.. code-block:: json

   {
       "status": "success",
       "data": {
           // Response data here
       }
   }

Error Response
^^^^^^^^^^^^^^

.. code-block:: json

   {
       "status": "error",
       "message": "Error description",
       "code": "ERROR_CODE"
   }

Status Codes
^^^^^^^^^^^^

The API uses standard HTTP status codes:

* ``200 OK`` - Request succeeded
* ``201 Created`` - Resource created successfully
* ``400 Bad Request`` - Invalid request data
* ``401 Unauthorized`` - Authentication required
* ``403 Forbidden`` - Insufficient permissions
* ``404 Not Found`` - Resource not found
* ``422 Unprocessable Entity`` - Validation error
* ``500 Internal Server Error`` - Server error

Rate Limiting
-------------

.. note::
   Rate limiting will be implemented in Phase 5 (Security Implementation).

CORS
----

Cross-Origin Resource Sharing (CORS) is enabled for all origins in development mode.

In production, CORS will be restricted to specific frontend domains.

API Versioning
--------------

The API uses URL-based versioning:

* **Current version**: ``v1``
* **Base path**: ``/api/v1``

Future versions will be available at ``/api/v2``, ``/api/v3``, etc.

Deprecation Policy
^^^^^^^^^^^^^^^^^^

When a new API version is released:

1. The previous version will be supported for a minimum of 6 months
2. Deprecation notices will be included in API responses
3. Documentation will clearly indicate deprecated endpoints
