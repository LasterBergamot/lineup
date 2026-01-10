Getting Started
===============

This guide will help you get the Lineup API up and running on your local machine.

Prerequisites
-------------

Before you begin, ensure you have the following installed:

* **Python 3.11 or higher** - The project requires Python 3.11+
* **Poetry** - For dependency management (install via ``pip install poetry``)
* **Docker** (optional) - For containerized development
* **Docker Compose** (optional) - For running the full stack locally

Installation
------------

1. Clone the Repository
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git clone https://github.com/your-org/lineup.git
   cd lineup

2. Configure Poetry
^^^^^^^^^^^^^^^^^^^

Configure Poetry to create virtual environments in the project directory:

.. code-block:: bash

   poetry config virtualenvs.in-project true

3. Install Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

Install all project dependencies and create the virtual environment:

.. code-block:: bash

   poetry install

This will create a ``.venv`` directory in the project root with all dependencies installed.

Virtual Environment
-------------------

Activating the Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

**On Windows (PowerShell):**

.. code-block:: powershell

   .\.venv\Scripts\Activate.ps1

**On Windows (Command Prompt):**

.. code-block:: cmd

   .\.venv\Scripts\activate.bat

**On Linux/macOS:**

.. code-block:: bash

   source .venv/bin/activate

**Using Poetry (cross-platform):**

.. code-block:: bash

   poetry shell

Running Without Activation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can run commands directly using Poetry without activating:

.. code-block:: bash

   poetry run pytest
   poetry run python run.py

Configuration
-------------

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Create a ``.env`` file in the project root (copy from ``.env.example`` if available):

.. code-block:: bash

   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here

Available environments:

* ``development`` - Development mode with debug enabled
* ``testing`` - Testing mode for running tests
* ``production`` - Production mode (requires SECRET_KEY)

Running the Application
-----------------------

Development Mode
^^^^^^^^^^^^^^^^

Start the Flask development server:

.. code-block:: bash

   poetry run python run.py

The application will start on ``http://localhost:5000``

Test the health endpoint:

.. code-block:: bash

   curl http://localhost:5000/api/v1/health

Expected response:

.. code-block:: json

   {
       "status": "healthy",
       "timestamp": "2026-01-10T12:00:00.000000"
   }

Docker Development
^^^^^^^^^^^^^^^^^^

Using Docker Compose (recommended for full stack):

.. code-block:: bash

   # Start all services
   docker-compose up

   # Start in background
   docker-compose up -d

   # View logs
   docker-compose logs -f api

   # Stop services
   docker-compose down

Services available:

* **API**: http://localhost:5000
* **PostgreSQL**: localhost:5432
* **pgAdmin**: http://localhost:5050

See the README.md for database credentials.

Running Tests
-------------

Run all tests:

.. code-block:: bash

   poetry run pytest

Run with coverage:

.. code-block:: bash

   poetry run pytest --cov=app --cov=config --cov-report=html

View coverage report by opening ``htmlcov/index.html`` in your browser.

Run specific test types:

.. code-block:: bash

   # Unit tests only
   poetry run pytest tests/unit

   # Integration tests only
   poetry run pytest tests/integration

   # E2E tests only
   poetry run pytest tests/e2e

Code Quality
------------

The project includes several code quality tools.

Run All Checks
^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python scripts/check_all.py

This runs Black, Flake8, MyPy, and pytest with coverage in sequence.

Individual Tools
^^^^^^^^^^^^^^^^

**Black (formatter):**

.. code-block:: bash

   # Format code
   poetry run black app config tests

   # Check formatting
   poetry run black --check app config tests

**Flake8 (linter):**

.. code-block:: bash

   poetry run flake8 app config tests

**MyPy (type checker):**

.. code-block:: bash

   poetry run mypy app config

Next Steps
----------

* Read the :doc:`api/index` to understand the API structure
* Check :doc:`development` for the development roadmap
* See :doc:`contributing` to learn how to contribute

Troubleshooting
---------------

Virtual Environment Issues
^^^^^^^^^^^^^^^^^^^^^^^^^^

If the virtual environment is not working:

.. code-block:: bash

   # Remove existing venv
   rm -rf .venv  # Linux/macOS
   # or
   Remove-Item -Recurse -Force .venv  # Windows PowerShell

   # Recreate
   poetry config virtualenvs.in-project true
   poetry install

Port Already in Use
^^^^^^^^^^^^^^^^^^^

If port 5000 is already in use:

* Find and stop the process using port 5000
* Or modify the port in ``run.py`` or use environment variable ``FLASK_RUN_PORT``

Docker Issues
^^^^^^^^^^^^^

If Docker containers fail to start:

.. code-block:: bash

   # Remove all containers and volumes
   docker-compose down -v

   # Rebuild and start
   docker-compose up --build
