# Lineup API Documentation

This directory contains the Sphinx documentation for the Lineup API project.

## Building the Documentation

### Prerequisites

Ensure you have the project dependencies installed:

```bash
poetry install
```

### Build Commands

**Using Sphinx directly:**

```bash
cd docs
poetry run sphinx-build -b html . _build
```

**Using make (Linux/macOS):**

```bash
cd docs
make html
```

**Using make.bat (Windows):**

```bash
cd docs
.\make.bat html
```

### Viewing the Documentation

After building, open `_build/index.html` in your web browser:

**Windows:**
```bash
start _build/index.html
```

**Linux:**
```bash
xdg-open _build/index.html
```

**macOS:**
```bash
open _build/index.html
```

## Documentation Structure

```
docs/
├── conf.py                 # Sphinx configuration
├── index.rst              # Main documentation page
├── getting_started.rst    # Installation and setup guide
├── development.rst        # Development guide
├── deployment.rst         # Deployment guide
├── contributing.rst       # Contributing guidelines
├── api/                   # API documentation
│   ├── index.rst         # API overview
│   ├── endpoints.rst     # API endpoints
│   └── modules.rst       # Python module documentation
├── _static/              # Custom static files (CSS, images)
├── _templates/           # Custom Sphinx templates
└── _build/               # Generated documentation (git-ignored)
```

## Writing Documentation

### reStructuredText Syntax

Documentation is written in reStructuredText (.rst) format.

**Basic formatting:**

```rst
# Heading 1
===========

Heading 2
---------

Heading 3
^^^^^^^^^

**bold text**

*italic text*

``code text``
```

**Code blocks:**

```rst
.. code-block:: python

   def example():
       return "Hello"
```

**Links:**

```rst
:doc:`other_page`  # Link to another doc page
:ref:`section-label`  # Link to a section
`External Link <https://example.com>`_
```

**Notes and warnings:**

```rst
.. note::
   This is a note.

.. warning::
   This is a warning.
```

### API Endpoint Documentation

Use HTTP domain directives for API endpoints:

```rst
.. http:get:: /api/v1/endpoint

   Description of the endpoint.

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:5000/api/v1/endpoint

   **Example Response:**

   .. code-block:: json

      {
          "status": "success"
      }

   :statuscode 200: Success
   :statuscode 404: Not found
```

### Auto-documenting Python Code

Use autodoc directives to document Python modules:

```rst
.. automodule:: app.routes.health
   :members:
   :undoc-members:
   :show-inheritance:
```

**Requirements for autodoc:**
- Python modules must be importable
- Add docstrings to all public functions/classes
- Use Google-style docstrings (configured in conf.py)

### Google-style Docstrings

```python
def function(arg1: str, arg2: int) -> bool:
    """Brief description of function.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
    """
    pass
```

## Sphinx Extensions

Currently enabled extensions (see `conf.py`):

- `sphinx.ext.autodoc` - Auto-generate docs from docstrings
- `sphinx.ext.viewcode` - Add links to source code
- `sphinx.ext.napoleon` - Google/NumPy docstring support
- `sphinx.ext.intersphinx` - Link to other projects' docs
- `sphinx.ext.todo` - TODO items support
- `sphinx.ext.coverage` - Documentation coverage checking
- `sphinxcontrib.httpdomain` - HTTP endpoint documentation

## Checking Documentation Coverage

Check which modules lack documentation:

```bash
cd docs
poetry run sphinx-build -b coverage . _build
cat _build/python.txt
```

## Cleaning Build Files

Remove generated documentation:

**Linux/macOS:**
```bash
cd docs
make clean
```

**Windows:**
```bash
cd docs
.\make.bat clean
```

**Or manually:**
```bash
rm -rf _build  # Linux/macOS
Remove-Item -Recurse -Force _build  # Windows PowerShell
```

## Sphinx Theme

The documentation uses the **Read the Docs** theme (`sphinx_rtd_theme`).

Theme configuration is in `conf.py` under `html_theme_options`.

## Adding New Documentation

1. Create a new `.rst` file in the appropriate directory
2. Add content using reStructuredText syntax
3. Include the file in a `toctree` directive in a parent document
4. Build and verify the documentation

**Example:**

In `index.rst`:

```rst
.. toctree::
   :maxdepth: 2

   existing_page
   new_page
```

## Troubleshooting

### Build Errors

**"No module named 'app'"**
- Ensure you're running Sphinx with Poetry: `poetry run sphinx-build`
- Check that the project root is in Python path (see `sys.path.insert` in `conf.py`)

**"Unknown directive type"**
- Check that the required extension is enabled in `conf.py`
- Verify extension installation: `poetry show | grep sphinx`

**"Duplicate label"**
- Ensure section labels are unique across all documentation files

### Warnings

Warnings won't stop the build but should be fixed:
- Check referenced files exist
- Verify code blocks have valid syntax
- Ensure all toctree entries exist

## CI/CD Integration

Documentation building will be integrated into the CI/CD pipeline in Phase 4:

- Automatic documentation building on PR
- Documentation deployment to Read the Docs
- Documentation coverage checks

## References

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
- [sphinxcontrib-httpdomain](https://sphinxcontrib-httpdomain.readthedocs.io/)
