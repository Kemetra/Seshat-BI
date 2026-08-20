"""Spec 149 / #660 -- the vendor's closed (tool, operation) vocabulary.

The vendor exposes 21 coarse dispatcher tools, each taking a ``request`` object
whose ``operation`` field selects the action. So an authorized write is a PAIR,
not a single token, and the allowlist stores ``"<tool>.<operation>"``.

Two fail-closed rules:

* An unknown tool or operation RAISES. ``npx`` starts whatever the registry
  resolves; a typo that silently became a no-op would report success for a
  mutation that never happened.
* An unrecognised operation verb counts as a WRITE. Guessing read-only on an
  unknown verb is the fail-open direction, and this gate exists to prevent it.

**Why the connection and flush verbs sit in ``WRITE_OPERATIONS`` even though the
vendor annotates them ``readOnlyHint: true``.** Measured 2026-08-20:
``connection_operations.connectfolder`` and
``database_operations.exporttotmdlfolder`` both report ``readOnlyHint: true``, yet
the export rewrote all 11 TMDL files. The vendor's hint tracks MODEL-STATE
mutation; this vocabulary tracks "may this verb be issued without a cleared write
gate". Those are different questions, and for the gate's purpose the flush is
unambiguously a write. The two classifications are allowed to disagree; the runner
therefore applies the ``readOnlyHint`` cross-check ONLY to the authorized
operation, never to the connect or flush calls it issues itself.
"""

from __future__ import annotations

__all__ = [
    "READ_OPERATIONS",
    "VENDOR_TOOLS",
    "WRITE_OPERATIONS",
    "UnknownVendorOperation",
    "is_write",
    "parse_operation_id",
]

#: The 21 tools the server advertised via tools/list, probed 2026-08-20 against
#: @microsoft/powerbi-modeling-mcp@0.5.0-beta.12. A closed set on purpose.
VENDOR_TOOLS: frozenset[str] = frozenset(
    {
        "calculation_group_operations",
        "calendar_operations",
        "column_operations",
        "connection_operations",
        "culture_operations",
        "database_operations",
        "dax_query_operations",
        "function_operations",
        "measure_operations",
        "model_operations",
        "named_expression_operations",
        "object_translation_operations",
        "partition_operations",
        "perspective_operations",
        "query_group_operations",
        "relationship_operations",
        "security_role_operations",
        "table_operations",
        "trace_operations",
        "transaction_operations",
        "user_hierarchy_operations",
    }
)

#: Verbs that do not mutate model state.
#:
#: PROVENANCE, stated exactly (issue #660 review, H4): every verb here appears in
#: the ``Supported operations:`` sentence of a tool description returned by
#: ``tools/list`` on 2026-08-20 -- 13 of the 21 tools publish such a list, 80
#: distinct verbs in total. Verbs seen ONLY in a tool's parameter documentation
#: are deliberately NOT listed as reads: an unevidenced verb misfiled here would
#: skip the write-path treatment entirely (no readOnlyHint cross-check, no flush,
#: ``succeeded=True``), which is the fail-OPEN direction. Absent from this set,
#: they fail closed instead -- see :func:`is_write`.
#:
#: Widening this set requires evidence from the server, not inference from a
#: name: ``database_operations.ExportToTmdlFolder`` looks like a read, reports
#: ``readOnlyHint: true``, and rewrites 11 files.
READ_OPERATIONS: frozenset[str] = frozenset(
    {
        "CheckStatusOfRefreshWithAPI",
        "ExportJSON",
        "ExportTMDL",
        "ExportTMSL",
        "Fetch",
        "Find",
        "Get",
        "GetColumnGroups",
        "GetColumns",
        "GetConnection",
        "GetGroup",
        "GetHierarchies",
        "GetItems",
        "GetMeasures",
        "GetStats",
        "GetStatus",
        "GetTables",
        "Help",
        "List",
        "ListActive",
        "ListColumnGroups",
        "ListColumns",
        "ListConnections",
        "ListGroups",
        "ListHierarchies",
        "ListItems",
        "ListLocalInstances",
        "ListMeasures",
        "ListTables",
        "Validate",
    }
)

#: The mutating verbs. Membership here is ADVISORY -- :func:`is_write` keys off
#: absence from ``READ_OPERATIONS``, so an unlisted verb is already treated as a
#: write. This set therefore also carries verbs known only from parameter
#: documentation: listing a write is safe in a way listing a read is not.
#:
#: ``ConnectFolder`` and ``ExportToTmdlFolder`` are here for the GATE's purposes
#: -- see the module docstring on why this deliberately disagrees with the
#: vendor's own ``readOnlyHint``.
WRITE_OPERATIONS: frozenset[str] = frozenset(
    {
        "Activate",
        "AddColumns",
        "AddHierarchies",
        "AddLevels",
        "AddMeasures",
        "AddTables",
        "Begin",
        "CancelRefresh",
        "CancelRefreshWithAPI",
        "Clear",
        "ClearCache",
        "Commit",
        "Connect",
        "ConnectBimFile",
        "ConnectFabric",
        "ConnectFolder",
        "Create",
        "CreateColumnGroups",
        "CreateFieldParameter",
        "CreateFromTMDL",
        "CreateGroup",
        "CreateItems",
        "CreateParameter",
        "CreatePermissions",
        "Deactivate",
        "Delete",
        "DeleteColumnGroups",
        "DeleteGroup",
        "DeleteItems",
        "DeletePermissions",
        "DeployToFabric",
        "Disconnect",
        "Execute",
        "ExportToBimFile",
        "ExportToTmdlFolder",
        "ImportFromBimFile",
        "ImportFromTmdlFolder",
        "MarkAsDateTable",
        "Move",
        "Pause",
        "RefreshWithAPI",
        "RefreshWithXMLA",
        "RemoveColumns",
        "RemoveHierarchies",
        "RemoveLevels",
        "RemoveMeasures",
        "RemoveTables",
        "Rename",
        "RenameGroup",
        "RenameItems",
        "RenameLevels",
        "ReorderItems",
        "ReorderLevels",
        "Resume",
        "Rollback",
        "Start",
        "Stop",
        "Update",
        "UpdateColumnGroups",
        "UpdateGroup",
        "UpdateItems",
        "UpdateLevels",
        "UpdateParameter",
        "UpdatePermissions",
        "UpdateTables",
    }
)


class UnknownVendorOperation(ValueError):
    """The allowlist named a tool or operation the vendor does not expose."""


def parse_operation_id(operation_id: str) -> tuple[str, str]:
    """Split the dotted pair and validate BOTH halves.

    The pre-#660 single-token form is rejected rather than reinterpreted: it
    encoded a CLI flag that never existed, so accepting it would carry the bug
    forward under a new name.
    """
    tool, separator, operation = operation_id.partition(".")
    if not separator or not operation:
        raise UnknownVendorOperation(
            f"{operation_id!r} is not a <tool>.<operation> pair"
        )
    if tool not in VENDOR_TOOLS:
        raise UnknownVendorOperation(f"unknown vendor tool: {tool!r}")
    if operation not in READ_OPERATIONS and operation not in WRITE_OPERATIONS:
        raise UnknownVendorOperation(f"unknown vendor operation: {operation!r}")
    return tool, operation


def is_write(operation: str) -> bool:
    """True unless the verb is a KNOWN read. Unknown verbs fail closed."""
    return operation not in READ_OPERATIONS
