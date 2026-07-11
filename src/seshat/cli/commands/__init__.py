"""Per-command CLI handlers (CodeScene hotspot split of the former cli.py).

Each module is imported LAZILY from ``seshat.cli.main``'s dispatcher, mirroring
the pre-split behavior where e.g. ``from .theme_gen import theme_gen_main`` lived
inside the ``if args.command == "theme-gen":`` branch. This package itself stays
import-light: no submodule is imported here at package-init time.
"""
