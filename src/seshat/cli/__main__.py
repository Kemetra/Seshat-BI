"""Make ``python -m seshat.cli ...`` invoke the CLI instead of being a silent no-op.

On a PACKAGE (not a single module), ``python -m pkg`` runs ``pkg/__main__.py``,
never ``pkg/__init__.py``'s ``if __name__ == "__main__"`` guard -- so this file is
required, not optional, now that ``cli`` is a package. The installed ``retail``
console script (pyproject ``[project.scripts]``) calls ``seshat.cli:main`` directly
and never imports this module.
"""

import sys

from seshat.cli import main

if __name__ == "__main__":
    sys.exit(main())
