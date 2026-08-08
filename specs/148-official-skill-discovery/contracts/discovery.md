# Contract: Official skill discovery

For each declared official skill component and harness:

1. resolve the catalog component and exact locked upstream identity;
2. prove the installed payload and required paths;
3. classify activation through the declared harness mechanism;
4. prove each expected discovered skill identity;
5. return the earliest truthful next action when any proof fails.

The contract forbids inferring discovery from clone presence, copying upstream
skill bodies, mutating global harness state during detection, and recording a
discoverable lock state without all proofs.
