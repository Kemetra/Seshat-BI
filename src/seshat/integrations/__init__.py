"""Curated analytics-stack integration: catalog, resolvers, and the lock file.

Seshat integrates mature analytics tools rather than rebuilding them. That is
only safe if every borrowed component is pinned to something that cannot move
under the operator, so this package implements one resolution model:

    discover latest compatible release
    -> resolve exact version/tag/commit/hash
    -> show plan
    -> require explicit approval
    -> install in isolation
    -> validate
    -> atomically write the lock file

The modules split along that pipeline. `catalog` declares WHAT may be
installed (the single source of truth for profile membership and version
channels). `versions` holds the stable-release semantics shared with the
spec-136 co-resolution gate. `resolvers` turns a catalog entry into an exact
coordinate behind injectable protocols, so unit tests never touch the network.
`compat` decides whether a resolved set may be installed together. `lockfile`
records what actually landed.
"""

from __future__ import annotations
