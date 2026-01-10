Contributing Guide
==================

Thank you for your interest in contributing to the Lineup API project!

This guide will help you get started with contributing to the project.

Code of Conduct
---------------

* Be respectful and inclusive
* Welcome newcomers and help them get started
* Focus on constructive feedback
* Assume good intentions
* Keep discussions professional

Getting Started
---------------

1. Fork the Repository
^^^^^^^^^^^^^^^^^^^^^^

Fork the repository on GitHub and clone your fork:

.. code-block:: bash

   git clone https://github.com/your-username/lineup.git
   cd lineup

2. Set Up Development Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Follow the :doc:`getting_started` guide to set up your development environment.

3. Create a Branch
^^^^^^^^^^^^^^^^^^

Create a feature branch for your changes:

.. code-block:: bash

   git checkout -b feature/your-feature-name

Branch naming conventions:

* ``feature/<name>`` - New features
* ``bugfix/<name>`` - Bug fixes
* ``docs/<name>`` - Documentation changes
* ``refactor/<name>`` - Code refactoring
* ``test/<name>`` - Test additions or fixes

Development Workflow
--------------------

1. Make Your Changes
^^^^^^^^^^^^^^^^^^^^

* Follow the :doc:`development` guide for coding standards
* Write or update tests for your changes
* Update documentation as needed
* Keep commits focused and atomic

2. Run Quality Checks
^^^^^^^^^^^^^^^^^^^^^^

Before committing, run all quality checks:

.. code-block:: bash

   poetry run python scripts/check_all.py

This runs:

* Black (code formatting)
* Flake8 (linting)
* MyPy (type checking)
* Pytest (tests with coverage)

Fix any issues before proceeding.

3. Run Tests
^^^^^^^^^^^^

Ensure all tests pass:

.. code-block:: bash

   poetry run pytest

Add new tests for your changes:

* Unit tests for new functions/classes
* Integration tests for API endpoints
* E2E tests for complete workflows

4. Commit Your Changes
^^^^^^^^^^^^^^^^^^^^^^^

Use conventional commit messages:

.. code-block:: bash

   git add .
   git commit -m "feat(api): add lineup creation endpoint"

Commit message format:

.. code-block:: text

   <type>(<scope>): <description>

   [optional body]

   [optional footer]

**Types:**

* ``feat`` - New feature
* ``fix`` - Bug fix
* ``docs`` - Documentation only
* ``style`` - Formatting changes
* ``refactor`` - Code refactoring
* ``test`` - Test additions/changes
* ``chore`` - Maintenance tasks

5. Push to Your Fork
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   git push origin feature/your-feature-name

6. Create Pull Request
^^^^^^^^^^^^^^^^^^^^^^^

1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill in the pull request template
5. Submit the pull request

Pull Request Guidelines
-----------------------

Pull Request Template
^^^^^^^^^^^^^^^^^^^^^^

When creating a pull request, include:

**Description:**

* What changes does this PR introduce?
* Why is this change needed?
* What issue does it fix? (if applicable)

**Changes:**

* List of specific changes made

**Testing:**

* What tests were added or modified?
* How was this tested?

**Checklist:**

* [ ] All tests pass
* [ ] Code follows style guidelines
* [ ] Documentation updated
* [ ] Commit messages follow convention
* [ ] No breaking changes (or documented if necessary)

Code Review Process
^^^^^^^^^^^^^^^^^^^

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: Maintainers review your code
3. **Feedback**: Address any feedback or requested changes
4. **Approval**: Once approved, maintainers will merge your PR
5. **Merge**: Your changes are merged into the main codebase

Addressing Feedback
^^^^^^^^^^^^^^^^^^^

If changes are requested:

.. code-block:: bash

   # Make the requested changes
   git add .
   git commit -m "fix: address code review feedback"
   git push origin feature/your-feature-name

The pull request will automatically update.

Types of Contributions
----------------------

Code Contributions
^^^^^^^^^^^^^^^^^^

* Implement new features
* Fix bugs
* Improve performance
* Refactor code

Documentation Contributions
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Improve existing documentation
* Add missing documentation
* Fix typos and errors
* Add examples and tutorials

Testing Contributions
^^^^^^^^^^^^^^^^^^^^^

* Add missing tests
* Improve test coverage
* Add integration or E2E tests
* Improve test quality

Bug Reports
^^^^^^^^^^^

If you find a bug, please create an issue with:

* **Title**: Brief description of the bug
* **Description**: Detailed description of the issue
* **Steps to Reproduce**: How to reproduce the bug
* **Expected Behavior**: What should happen
* **Actual Behavior**: What actually happens
* **Environment**: OS, Python version, etc.
* **Screenshots**: If applicable

Feature Requests
^^^^^^^^^^^^^^^^

For feature requests, create an issue with:

* **Title**: Brief description of the feature
* **Description**: Detailed description of the feature
* **Use Case**: Why is this feature needed?
* **Proposed Solution**: How could this be implemented?
* **Alternatives**: Other solutions considered

Coding Standards
----------------

Python Style
^^^^^^^^^^^^

* Follow **PEP 8** style guide
* Maximum line length: **100 characters**
* Use **type hints** for function parameters and return values
* Write **docstrings** for all public APIs

Code Quality
^^^^^^^^^^^^

* Run Black for automatic formatting
* Ensure Flake8 passes (no linting errors)
* Use MyPy for type checking
* Maintain or improve test coverage

Example Code
^^^^^^^^^^^^

.. code-block:: python

   from typing import Dict, Optional
   import logging

   logger = logging.getLogger(__name__)


   def create_lineup(
       match_id: str,
       team_id: str,
       players: list[dict],
       notes: Optional[str] = None
   ) -> Dict[str, any]:
       """Create a new lineup for a match.

       Args:
           match_id: The unique identifier for the match
           team_id: The unique identifier for the team
           players: List of player dictionaries with positions
           notes: Optional notes about the lineup

       Returns:
           Dictionary containing the created lineup data with keys:
           - lineup_id: The unique identifier for the lineup
           - created_at: Timestamp of creation

       Raises:
           ValueError: If match_id or team_id is invalid
           ValidationError: If player data is invalid
       """
       logger.info(f"Creating lineup for match {match_id}")
       
       # Validate inputs
       if not match_id or not team_id:
           raise ValueError("match_id and team_id are required")
       
       # Implementation here
       lineup = {
           "lineup_id": "generated-uuid",
           "match_id": match_id,
           "team_id": team_id,
           "players": players,
           "notes": notes,
           "created_at": "2026-01-10T12:00:00"
       }
       
       return lineup

Testing Standards
^^^^^^^^^^^^^^^^^

* Write tests for all new code
* Aim for >80% code coverage
* Use descriptive test names
* Each test should be independent
* Use fixtures for common setup

.. code-block:: python

   import pytest
   from app import create_app


   @pytest.fixture
   def client():
       """Create test client for API testing."""
       app = create_app("testing")
       with app.test_client() as client:
           yield client


   def test_create_lineup_success(client):
       """Test successful lineup creation returns 201."""
       payload = {
           "match_id": "test-match-id",
           "team_id": "test-team-id",
           "players": [
               {"player_id": "p1", "position": "goalkeeper", "number": 1}
           ]
       }
       
       response = client.post("/api/v1/lineups", json=payload)
       
       assert response.status_code == 201
       assert "lineup_id" in response.json["data"]


   def test_create_lineup_missing_match_id(client):
       """Test lineup creation without match_id returns 400."""
       payload = {
           "team_id": "test-team-id",
           "players": []
       }
       
       response = client.post("/api/v1/lineups", json=payload)
       
       assert response.status_code == 400
       assert "match_id" in response.json["message"].lower()

Documentation Standards
^^^^^^^^^^^^^^^^^^^^^^^

* Use clear, concise language
* Include code examples
* Update documentation when changing functionality
* Use proper reStructuredText formatting

Getting Help
------------

If you need help:

* Check the :doc:`getting_started` guide
* Review the :doc:`development` guide
* Search existing GitHub issues
* Create a new issue with your question
* Reach out to maintainers

Issue Labels
------------

Issues are labeled to help contributors find what they're looking for:

* ``good first issue`` - Good for newcomers
* ``help wanted`` - Extra attention needed
* ``bug`` - Something isn't working
* ``enhancement`` - New feature or request
* ``documentation`` - Documentation improvements
* ``question`` - Questions about the project
* ``priority: high`` - High priority issue
* ``priority: low`` - Low priority issue

License
-------

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

Recognition
-----------

Contributors will be recognized in:

* GitHub Contributors page
* Release notes for significant contributions
* Project documentation (if applicable)

Thank You!
----------

Thank you for contributing to the Lineup API project! Your contributions help make this project better for everyone.

Questions?
----------

If you have questions about contributing, feel free to:

* Open an issue with the ``question`` label
* Reach out to the maintainers
* Check the project documentation

We're here to help! 🚀
