Development Guide
=================

This guide provides information for developers working on the Lineup API project.

Development Roadmap
-------------------

The project follows a phased development approach as outlined in ``TODO.md``.

Current Phase: Phase 1 - Project Foundation & Setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Completed:**

* ✅ Phase 1.1: Python project initialization with Poetry
* ✅ Phase 1.2: Project structure setup (Flask API skeleton)
* ✅ Phase 1.3: Code quality tools configuration
* ✅ Phase 1.4: Testing framework setup (pytest with testing pyramid)
* ✅ Phase 1.5: Docker containerization
* ✅ Phase 1.6: Initial documentation structure

**Upcoming:**

* ⏳ Phase 1.7: GitHub repository structure setup

Upcoming Phases
^^^^^^^^^^^^^^^

* **Phase 2**: Core API Development (Water Polo - Hungarian Leagues)
* **Phase 3**: Database Integration (PostgreSQL)
* **Phase 4**: Cloud Deployment & CI/CD (AWS)
* **Phase 5**: Security Implementation (JWT, OAuth)
* **Phase 6**: API Finalization & Frontend Preparation

See ``TODO.md`` in the project root for detailed task breakdown.

Project Structure
-----------------

.. code-block:: text

   lineup/
   ├── app/                    # Flask application
   │   ├── __init__.py        # App factory
   │   └── routes/            # API routes
   │       ├── __init__.py
   │       └── health.py      # Health check endpoint
   ├── config/                # Configuration modules
   │   └── __init__.py        # Config classes
   ├── tests/                 # Test suite
   │   ├── unit/             # Unit tests
   │   ├── integration/      # Integration tests
   │   └── e2e/              # End-to-end tests
   ├── docs/                  # Documentation (Sphinx)
   ├── scripts/              # Utility scripts
   ├── docker-compose.yml    # Docker Compose config
   ├── Dockerfile            # Docker image config
   ├── pyproject.toml        # Poetry config
   ├── .flake8               # Flake8 config
   ├── .dockerignore         # Docker ignore rules
   └── run.py                # Application entry point

Coding Standards
----------------

The project follows strict coding standards to maintain high code quality.

Python Style Guide
^^^^^^^^^^^^^^^^^^

* Follow **PEP 8** style guide
* Use **type hints** for function parameters and return values
* Write **docstrings** for all public modules, classes, and functions
* Maximum line length: **100 characters**

Docstring Format
^^^^^^^^^^^^^^^^

Use Google-style docstrings:

.. code-block:: python

   def create_lineup(match_id: str, team_id: str) -> dict:
       """Create a new lineup for a match.

       Args:
           match_id: The unique identifier for the match
           team_id: The unique identifier for the team

       Returns:
           A dictionary containing the created lineup data

       Raises:
           ValueError: If match_id or team_id is invalid
           DatabaseError: If database operation fails
       """
       pass

Code Quality Tools
^^^^^^^^^^^^^^^^^^

All code must pass these checks before committing:

1. **Black** - Code formatter (automated)
2. **Flake8** - Linter (style and quality)
3. **MyPy** - Type checker
4. **Pytest** - All tests must pass

Run all checks:

.. code-block:: bash

   poetry run python scripts/check_all.py

Testing Strategy
----------------

The project follows the **Testing Pyramid** approach.

Test Levels
^^^^^^^^^^^

1. **Unit Tests** (``tests/unit/``)
   
   * Test individual functions and classes in isolation
   * Fast execution
   * High coverage (aim for >90%)
   * Mock external dependencies

2. **Integration Tests** (``tests/integration/``)
   
   * Test interaction between components
   * Test database operations
   * Test API endpoints
   * Moderate execution speed

3. **End-to-End Tests** (``tests/e2e/``)
   
   * Test complete user flows
   * Test full API workflows
   * Slower execution
   * Focus on critical paths

Test Guidelines
^^^^^^^^^^^^^^^

* Write tests before or alongside code (TDD approach)
* Each test should be independent and isolated
* Use descriptive test names: ``test_<what>_<condition>_<expected_result>``
* Use fixtures for common setup
* Mock external services and databases in unit tests
* Aim for >80% code coverage overall

Example Test
^^^^^^^^^^^^

.. code-block:: python

   import pytest
   from app import create_app

   @pytest.fixture
   def app():
       """Create application for testing."""
       app = create_app("testing")
       yield app

   @pytest.fixture
   def client(app):
       """Create test client."""
       return app.test_client()

   def test_health_endpoint_returns_200(client):
       """Test that health endpoint returns 200 OK."""
       response = client.get("/api/v1/health")
       assert response.status_code == 200
       assert response.json["status"] == "healthy"

Running Tests
^^^^^^^^^^^^^

.. code-block:: bash

   # Run all tests
   poetry run pytest

   # Run with coverage
   poetry run pytest --cov=app --cov=config

   # Run specific test file
   poetry run pytest tests/unit/test_config.py

   # Run specific test
   poetry run pytest tests/unit/test_config.py::test_development_config

   # Run with verbose output
   poetry run pytest -v

Git Workflow
------------

Branching Strategy
^^^^^^^^^^^^^^^^^^

* ``main`` - Production-ready code
* ``develop`` - Integration branch for features
* ``feature/<name>`` - Feature branches
* ``bugfix/<name>`` - Bug fix branches
* ``hotfix/<name>`` - Production hotfixes

Commit Messages
^^^^^^^^^^^^^^^

Follow the Conventional Commits specification:

.. code-block:: text

   <type>(<scope>): <description>

   [optional body]

   [optional footer]

**Types:**

* ``feat`` - New feature
* ``fix`` - Bug fix
* ``docs`` - Documentation changes
* ``style`` - Code style changes (formatting)
* ``refactor`` - Code refactoring
* ``test`` - Adding or updating tests
* ``chore`` - Maintenance tasks

**Examples:**

.. code-block:: text

   feat(api): add lineup creation endpoint
   
   fix(validation): correct player number validation
   
   docs: update API documentation for health endpoint
   
   test(integration): add tests for lineup endpoints

Pull Request Process
^^^^^^^^^^^^^^^^^^^^

1. Create a feature branch from ``develop``
2. Make your changes
3. Ensure all tests pass
4. Ensure all code quality checks pass
5. Update documentation if needed
6. Create pull request to ``develop``
7. Address code review feedback
8. Merge after approval

Docker Development
------------------

Building Images
^^^^^^^^^^^^^^^

.. code-block:: bash

   # Development image
   docker build --target development -t lineup:dev .

   # Production image
   docker build --target production -t lineup:prod .

Running with Docker Compose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Start all services
   docker-compose up

   # Start in background
   docker-compose up -d

   # View logs
   docker-compose logs -f api

   # Execute commands in container
   docker-compose exec api poetry run pytest

   # Stop services
   docker-compose down

Environment Variables
---------------------

Development Environment
^^^^^^^^^^^^^^^^^^^^^^^

Create a ``.env`` file:

.. code-block:: bash

   FLASK_ENV=development
   FLASK_DEBUG=1
   DATABASE_URL=postgresql://lineup:lineup_dev@localhost:5432/lineup_db

Testing Environment
^^^^^^^^^^^^^^^^^^^

Environment variables for testing are configured in ``pytest.ini`` or ``pyproject.toml``.

Production Environment
^^^^^^^^^^^^^^^^^^^^^^

.. warning::
   Never commit production credentials to version control!

Production environment variables should be:

* Set in the deployment environment (AWS, etc.)
* Stored in secure secrets management (AWS Secrets Manager)
* Never included in code or configuration files

Adding Dependencies
-------------------

Always use Poetry to manage dependencies:

.. code-block:: bash

   # Add production dependency
   poetry add <package>

   # Add development dependency
   poetry add --group dev <package>

   # Update dependencies
   poetry update

   # Remove dependency
   poetry remove <package>

After adding dependencies, commit both ``pyproject.toml`` and ``poetry.lock``.

Debugging
---------

Using Python Debugger
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pdb; pdb.set_trace()

Or use VS Code / Cursor debugger with breakpoints.

Debug Logging
^^^^^^^^^^^^^

.. code-block:: python

   import logging

   logger = logging.getLogger(__name__)
   logger.debug("Debug message")
   logger.info("Info message")
   logger.warning("Warning message")
   logger.error("Error message")

Performance Profiling
^^^^^^^^^^^^^^^^^^^^^

.. note::
   Performance profiling tools and guidelines will be added in Phase 6.

Contributing
------------

See :doc:`contributing` for detailed contribution guidelines.

Resources
---------

* Flask Documentation: https://flask.palletsprojects.com/
* pytest Documentation: https://docs.pytest.org/
* Poetry Documentation: https://python-poetry.org/docs/
* Docker Documentation: https://docs.docker.com/
* Python Type Hints: https://docs.python.org/3/library/typing.html
