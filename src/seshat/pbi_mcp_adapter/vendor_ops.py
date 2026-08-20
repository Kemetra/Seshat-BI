"""Spec 149 / #660 -- the vendor's closed (tool, operation) vocabulary.

The vendor exposes 21 coarse dispatcher tools, each taking a ``request`` object
whose ``operation`` field selects the action. So an authorized write is a PAIR,
not a single token, and the allowlist stores ``"<tool>.<operation>"``.

**The vocabulary is PER TOOL, not a global verb set** (issue #660 re-review, H4).
A flat set plus independent validation of each half authorizes the whole
cross-product, so a verb evidenced under one tool would be accepted for every
tool. Classified as a read, an operation gets no ``readOnlyHint`` cross-check, no
flush, and ``succeeded=True`` -- and ``Export*`` is the exact family this repo
proved rewrites 11 files while self-reporting ``readOnlyHint: true``. Per-tool
membership closes that: a verb is accepted only for a tool the server showed it
under.

Three fail-closed rules:

* An unknown tool, or a verb not evidenced FOR THAT TOOL, RAISES. ``npx`` starts
  whatever the registry resolves; a pair that silently became a no-op would
  report success for a mutation that never happened.
* **A tool with no evidenced operation list permits NOTHING.** One of the 21
  (``partition_operations``) publishes no ``Supported operations:`` sentence, so
  it is absent here and every pair naming it is refused. An absent entry must
  never read as "anything goes".
* Any verb not in a tool's READ set is treated as a WRITE. Guessing read-only is
  the fail-open direction, and this gate exists to prevent it.

PROVENANCE, stated exactly: every pair below appears in the ``Supported
operations:`` sentence of that tool's own description, returned by ``tools/list``
against ``@microsoft/powerbi-modeling-mcp@0.5.0-beta.12`` on 2026-08-20 -- 20 of
21 tools publish such a list, **220 (tool, verb) pairs**. Verbs seen only in a
tool's parameter documentation are deliberately EXCLUDED: an unevidenced verb
admitted as a read is the fail-open direction.

``needs_payload`` is likewise the SERVER's own statement, from the
"For Create and Update use Definitions" clause in the same descriptions. Those
operations cannot be executed from a verb alone -- see :func:`requires_payload`
and the ``approved_definitions[]`` deferral in ``spec.md``.

Widening this map requires evidence from the server, not inference from a name:
``database_operations.ExportToTmdlFolder`` looks like a read, reports
``readOnlyHint: true``, and rewrote all 11 TMDL files (research.md R8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "TOOL_OPERATIONS",
    "VENDOR_TOOLS",
    "UnknownVendorOperation",
    "is_write",
    "parse_operation_id",
    "requires_payload",
]


@dataclass(frozen=True)
class _Verbs:
    """One tool's evidenced operations, split by what they need and do."""

    reads: frozenset[str]
    all_verbs: frozenset[str]
    #: Operations the server documents as requiring a ``Definitions`` block.
    needs_payload: frozenset[str] = field(default_factory=frozenset)


#: The evidenced (tool -> operations) map. A tool ABSENT here permits nothing.
TOOL_OPERATIONS: dict[str, _Verbs] = {
    "calculation_group_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "GetGroup",
                "GetItems",
                "Help",
                "ListGroups",
                "ListItems",
            }
        ),
        all_verbs=frozenset(
            {
                "CreateGroup",
                "CreateItems",
                "DeleteGroup",
                "DeleteItems",
                "ExportTMDL",
                "GetGroup",
                "GetItems",
                "Help",
                "ListGroups",
                "ListItems",
                "RenameGroup",
                "RenameItems",
                "ReorderItems",
                "UpdateGroup",
                "UpdateItems",
            }
        ),
    ),
    "calendar_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "GetColumnGroups",
                "Help",
                "List",
                "ListColumnGroups",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "CreateColumnGroups",
                "Delete",
                "DeleteColumnGroups",
                "ExportTMDL",
                "Get",
                "GetColumnGroups",
                "Help",
                "List",
                "ListColumnGroups",
                "Rename",
                "Update",
                "UpdateColumnGroups",
            }
        ),
    ),
    "column_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "Help",
                "List",
                "Rename",
                "Update",
            }
        ),
        needs_payload=frozenset(
            {
                "Create",
                "Update",
            }
        ),
    ),
    "connection_operations": _Verbs(
        reads=frozenset(
            {
                "GetConnection",
                "Help",
                "ListConnections",
                "ListLocalInstances",
            }
        ),
        all_verbs=frozenset(
            {
                "Connect",
                "ConnectBimFile",
                "ConnectFabric",
                "ConnectFolder",
                "Disconnect",
                "GetConnection",
                "Help",
                "ListConnections",
                "ListLocalInstances",
            }
        ),
    ),
    "culture_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "GetDetailsByLCID",
                "GetDetailsByName",
                "GetValidDetails",
                "GetValidNames",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "GetDetailsByLCID",
                "GetDetailsByName",
                "GetValidDetails",
                "GetValidNames",
                "Help",
                "List",
                "Rename",
                "Update",
            }
        ),
    ),
    "database_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "ExportTMSL",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "DeployToFabric",
                "ExportTMDL",
                "ExportTMSL",
                "ExportToBimFile",
                "ExportToTmdlFolder",
                "Help",
                "ImportFromBimFile",
                "ImportFromTmdlFolder",
                "List",
                "Update",
            }
        ),
    ),
    "dax_query_operations": _Verbs(
        reads=frozenset(
            {
                "Help",
                "Validate",
            }
        ),
        all_verbs=frozenset(
            {
                "ClearCache",
                "Execute",
                "Help",
                "Validate",
            }
        ),
    ),
    "function_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "Help",
                "List",
                "Rename",
                "Update",
            }
        ),
    ),
    "measure_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "Help",
                "List",
                "Move",
                "Rename",
                "Update",
            }
        ),
        needs_payload=frozenset(
            {
                "Create",
                "Update",
            }
        ),
    ),
    "model_operations": _Verbs(
        reads=frozenset(
            {
                "CheckStatusOfRefreshWithAPI",
                "ExportTMDL",
                "Get",
                "GetStats",
                "Help",
            }
        ),
        all_verbs=frozenset(
            {
                "CancelRefreshWithAPI",
                "CheckStatusOfRefreshWithAPI",
                "Create",
                "ExportTMDL",
                "Get",
                "GetStats",
                "Help",
                "RefreshWithAPI",
                "RefreshWithXMLA",
                "Rename",
                "Update",
            }
        ),
    ),
    "named_expression_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "CreateParameter",
                "Delete",
                "ExportTMDL",
                "Get",
                "Help",
                "List",
                "Rename",
                "Update",
                "UpdateParameter",
            }
        ),
    ),
    "object_translation_operations": _Verbs(
        reads=frozenset(
            {
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "Get",
                "Help",
                "List",
                "Update",
            }
        ),
    ),
    "perspective_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "GetColumns",
                "GetHierarchies",
                "GetMeasures",
                "GetTables",
                "Help",
                "List",
                "ListColumns",
                "ListHierarchies",
                "ListMeasures",
                "ListTables",
            }
        ),
        all_verbs=frozenset(
            {
                "AddColumns",
                "AddHierarchies",
                "AddMeasures",
                "AddTables",
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "GetColumns",
                "GetHierarchies",
                "GetMeasures",
                "GetTables",
                "Help",
                "List",
                "ListColumns",
                "ListHierarchies",
                "ListMeasures",
                "ListTables",
                "RemoveColumns",
                "RemoveHierarchies",
                "RemoveMeasures",
                "RemoveTables",
                "Rename",
                "Update",
                "UpdateTables",
            }
        ),
    ),
    "query_group_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "Help",
                "List",
                "Update",
            }
        ),
    ),
    "relationship_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Find",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Activate",
                "Create",
                "Deactivate",
                "Delete",
                "ExportTMDL",
                "Find",
                "Get",
                "Help",
                "List",
                "Rename",
                "Update",
            }
        ),
    ),
    "security_role_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "ExportTMSL",
                "Get",
                "GetEffectivePermissions",
                "GetPermissions",
                "Help",
                "List",
                "ListPermissions",
            }
        ),
        all_verbs=frozenset(
            {
                "Create",
                "CreatePermissions",
                "Delete",
                "DeletePermissions",
                "ExportTMDL",
                "ExportTMSL",
                "Get",
                "GetEffectivePermissions",
                "GetPermissions",
                "Help",
                "List",
                "ListPermissions",
                "Rename",
                "Update",
                "UpdatePermissions",
            }
        ),
    ),
    "table_operations": _Verbs(
        reads=frozenset(
            {
                "CheckStatusOfRefreshWithAPI",
                "ExportTMDL",
                "ExportTMSL",
                "Get",
                "GetSchema",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "CancelRefreshWithAPI",
                "CheckStatusOfRefreshWithAPI",
                "Create",
                "CreateFieldParameter",
                "Delete",
                "ExportTMDL",
                "ExportTMSL",
                "Get",
                "GetSchema",
                "Help",
                "List",
                "MarkAsDateTable",
                "RefreshWithAPI",
                "RefreshWithXMLA",
                "Rename",
                "Update",
            }
        ),
        needs_payload=frozenset(
            {
                "Create",
                "Update",
            }
        ),
    ),
    "trace_operations": _Verbs(
        reads=frozenset(
            {
                "ExportJSON",
                "Fetch",
                "Get",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "Clear",
                "ExportJSON",
                "Fetch",
                "Get",
                "Help",
                "List",
                "Pause",
                "Resume",
                "Start",
                "Stop",
            }
        ),
    ),
    "transaction_operations": _Verbs(
        reads=frozenset(
            {
                "GetStatus",
                "Help",
                "ListActive",
            }
        ),
        all_verbs=frozenset(
            {
                "Begin",
                "Commit",
                "GetStatus",
                "Help",
                "ListActive",
                "Rollback",
            }
        ),
    ),
    "user_hierarchy_operations": _Verbs(
        reads=frozenset(
            {
                "ExportTMDL",
                "Get",
                "GetColumns",
                "Help",
                "List",
            }
        ),
        all_verbs=frozenset(
            {
                "AddLevels",
                "Create",
                "Delete",
                "ExportTMDL",
                "Get",
                "GetColumns",
                "Help",
                "List",
                "RemoveLevels",
                "Rename",
                "RenameLevels",
                "ReorderLevels",
                "Update",
                "UpdateLevels",
            }
        ),
    ),
}

#: The 21 tools the server advertised via ``tools/list``. A superset of
#: ``TOOL_OPERATIONS``: a tool can exist and still authorize no operation,
#: because it published no operation list to derive one from.
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


class UnknownVendorOperation(ValueError):
    """The allowlist named a tool or operation the vendor does not expose."""


def parse_operation_id(operation_id: str) -> tuple[str, str]:
    """Split the dotted pair and validate the verb AGAINST THAT TOOL.

    The pre-#660 single-token form is rejected rather than reinterpreted: it
    encoded a CLI flag that never existed, so accepting it would carry the bug
    forward under a new name.

    Validating the halves independently would authorize the cross-product, so the
    verb is checked against the named tool's own evidenced set (re-review H4).
    """
    tool, separator, operation = operation_id.partition(".")
    if not separator or not operation:
        raise UnknownVendorOperation(
            f"{operation_id!r} is not a <tool>.<operation> pair"
        )
    if tool not in VENDOR_TOOLS:
        raise UnknownVendorOperation(f"unknown vendor tool: {tool!r}")
    known = TOOL_OPERATIONS.get(tool)
    if known is None:
        raise UnknownVendorOperation(
            f"{tool!r} publishes no evidenced operation list, so it authorizes "
            "nothing; refusing rather than guessing"
        )
    if operation not in known.all_verbs:
        raise UnknownVendorOperation(
            f"{operation!r} is not an evidenced operation of {tool!r}"
        )
    return tool, operation


def is_write(operation: str, tool: str | None = None) -> bool:
    """True unless the verb is a KNOWN read OF THAT TOOL. Fails closed.

    ``tool`` is optional only so a caller without it still gets the SAFE answer;
    pass it whenever known -- :func:`parse_operation_id` always returns both.
    """
    if tool is not None:
        known = TOOL_OPERATIONS.get(tool)
        return known is None or operation not in known.reads
    return not any(operation in verbs.reads for verbs in TOOL_OPERATIONS.values())


def requires_payload(tool: str, operation: str) -> bool:
    """Whether the SERVER documents this pair as needing a ``Definitions`` block.

    A ``Create``/``Update`` issued from a verb alone mutates nothing, so a run
    reporting success would be certifying a no-op. This adapter is forbidden to
    invent the definition (``spec.md``: "the adapter never invents the
    definition"), and the ``approved_definitions[]`` record that would supply one
    is deferred to a companion spec -- so such a pair must be REFUSED loudly
    rather than executed hollow (issue #660 re-review, C2).
    """
    known = TOOL_OPERATIONS.get(tool)
    return known is not None and operation in known.needs_payload
