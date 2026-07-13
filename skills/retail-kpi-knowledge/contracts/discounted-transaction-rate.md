# Discounted Transaction Rate - Metric Contract

ID: KPI-MC-14

**Business question**
How often do qualifying customer transactions carry a qualifying commercial discount?

**Business definition**
The share of an owner-defined eligible transaction population that meets the approved
definition of a discounted transaction. Both the discount qualification and the eligible
denominator are owner policy slots; this contract does not choose them.

**Formula in business terms**
Compare the count of qualifying discounted transactions with the count of eligible
transactions in the same approved scope. Recompute the relationship at every rollup.

**Derives from**
KPI-MC-04 (Transactions Count). The denominator is a policy-defined subset of the
Transactions Count population; the qualifying-discount numerator is a logical concept,
not a second copied formula.

**Required fields**
- transaction identifier at receipt grain *(confirmed concept)*
- discount qualification indicator or approved discount evidence *(assumption)*
- qualifying transaction status and business date *(assumption)*

**Grain**
Receipt grain, evaluated for an approved reporting scope.

**Additivity**
Non-additive. Recompute from the approved numerator and denominator at every rollup.

**Filters / exclusions**
- The owner defines which commercial discounts qualify.
- The owner defines the eligible transaction denominator.
- Exclusions for cancelled, return-only, and test activity must match the denominator
  policy.

**Validation checks**
- Confirm both populations use the same approved scope.
- Confirm a transaction is counted at most once in each population.
- Review policy changes before comparing periods.

**Implementation handoff notes (SQL / DAX / Python)**
Ratio intent only. Preserve the owner policy slots and recompute from receipt-level
populations; no implementation code is authored here.

**Priority**
Expansion wave.

**Owner**
Commercial and Finance.

**Status**
Seeded generic knowledge contract. Project use still requires approved decisions and
mapped source evidence.
