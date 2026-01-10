Lineup API Documentation
========================

Welcome to Lineup API's documentation!

Lineup API is a REST API for creating and managing sports team lineups with PDF export functionality. 
Initially focused on water polo in Hungarian leagues, the system is designed to be extensible to other sports.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   api/index
   development
   deployment
   contributing

Project Overview
----------------

The Lineup API project provides a backend REST API that enables:

* Creation and management of team lineups for various sports
* Validation of lineup data according to sport-specific rules
* Export of lineups to printable PDF documents (Rajtlista format for water polo)
* Data persistence and retrieval for teams, players, matches, and lineups

The project is designed with the following principles:

* **Security First**: High emphasis on security to meet industry standards
* **Quality Code**: Automated code quality checks and comprehensive testing
* **Scalability**: Designed to handle few users initially but with potential for growth
* **Extensibility**: Built to support multiple sports through abstraction and generalization

Current Status
--------------

The project is in **Phase 1** of development - Project Foundation & Setup.

See :doc:`development` for the current development roadmap and progress.

Features
--------

Current Features (Phase 1)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Flask-based REST API structure
* Health check endpoint
* Comprehensive testing framework (unit, integration, e2e tests)
* Code quality tools (Black, Flake8, MyPy, Coverage)
* Docker containerization with multi-stage builds
* Docker Compose for local development with PostgreSQL and pgAdmin
* CORS configuration for future frontend integration

Planned Features
^^^^^^^^^^^^^^^^

* Water polo lineup creation and validation (Phase 2)
* PDF generation for Rajtlista documents (Phase 2)
* Database integration with PostgreSQL (Phase 3)
* Cloud deployment on AWS with CI/CD (Phase 4)
* JWT authentication and OAuth integration (Phase 5)
* Full API documentation and frontend preparation (Phase 6)

Quick Links
-----------

* `GitHub Repository <https://github.com/your-org/lineup>`_ (Update with actual URL)
* :doc:`getting_started` - Get up and running quickly
* :doc:`api/index` - API Reference
* :doc:`development` - Development guide and roadmap
* :doc:`contributing` - How to contribute

Tech Stack
----------

* **Language**: Python 3.11+
* **Framework**: Flask 3.0+
* **Database**: PostgreSQL (planned)
* **Testing**: pytest
* **Code Quality**: Black, Flake8, MyPy, Coverage
* **Dependency Management**: Poetry
* **Containerization**: Docker & Docker Compose
* **CI/CD**: GitHub Actions (planned)
* **Documentation**: Sphinx + Read the Docs
* **Cloud Platform**: AWS (planned)

Support
-------

For issues, questions, or contributions:

* Open an issue on `GitHub Issues <https://github.com/your-org/lineup/issues>`_
* See :doc:`contributing` for contribution guidelines

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
