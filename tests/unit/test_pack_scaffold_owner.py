"""The scaffolded pack names its human owner exactly as given.

The owner is the named-human attribution for a pack, so a quote must not break
the manifest and a Windows `DOMAIN\\name` backslash must not be read as a YAML
escape that silently changes the name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.packs.model import PackError, PackSpec
from seshat.packs.scaffold import scaffold_pack
from seshat.packs.validator import validate_pack

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "owner", ["CORP\\ahmed", "CORP\\user", 'Ahmed "AJ" Shaaban', "Zoë Ångström"]
)
def test_the_owner_round_trips_exactly(tmp_path: Path, owner: str) -> None:
    written = scaffold_pack(tmp_path, PackSpec("acme.retail-kpis", "kpi", owner))
    manifest_path = next(path for path in written if path.endswith("seshat-pack.yaml"))

    manifest, findings = validate_pack(tmp_path, manifest_path)

    assert findings == []
    assert manifest is not None
    assert manifest.owner == owner


@pytest.mark.parametrize("owner", ["Ahmed\nShaaban", "CORP\x07hmed", "tab\there"])
def test_an_owner_with_control_characters_is_refused(tmp_path: Path, owner: str):
    with pytest.raises(PackError, match="owner"):
        scaffold_pack(tmp_path, PackSpec("acme.retail-kpis", "kpi", owner))
    assert not (tmp_path / "packs").exists()
