# Vehicle Allocation — Implementation Notes

**Date:** 2026-08-18
**Author:** M. Oshanreh
**Model:** PSRC Soundcast / ActivitySim (`soundcast/inputs/model/activitysim/configs`)
**ActivitySim version validated against:** `1000.dev3503` (editable dev build in `activitysim/.venv`)

---

## 1. Objective

Add the ActivitySim **`vehicle_allocation`** component downstream of the already-implemented
**`vehicle_type_choice`** module, and wire its output into tour and trip mode choice so that the
**selected vehicle's `auto_operating_cost`** drives the auto operating-cost terms — replacing the
single flat scalar `costPerMile: 18.29` (cents/mile) that was used for every household.

`vehicle_allocation` selects, for each tour and each occupancy level, one vehicle from the
household fleet (or a non-household vehicle). This is the first component in the Soundcast pipeline
that actually *consumes* `vehicle_type_choice` output — previously the `vehicles` table was produced
but never used by any behavioral model.

### Scope decision
The **"full feedback"** option was chosen (confirmed by the modeler): the allocated vehicle's
operating cost is fed back into mode choice. The alternative ("allocation only, produce
`selected_vehicle` for reporting but leave `costPerMile` in the utilities") was not taken.
Consequence: mode-choice results **will shift** relative to the flat-scalar version and the
component **will want local recalibration** before production use.

---

## 2. Model flow

```
auto_ownership ─▶ vehicle_type_choice ─▶ vehicle_allocation ─▶ tour_mode_choice_simulate
                                                            ├─▶ atwork_subtour_mode_choice
                                                            └─▶ trip_mode_choice
```

`vehicle_allocation` is inserted **after `non_mandatory_tour_scheduling`** and **before
`tour_mode_choice_simulate`** so that all non-atwork tours exist (with `start`/`end` times) when it
runs. Atwork subtours are created later and inherit their parent tour's vehicle.

### Occupancy → mode mapping
`OCCUPANCY_LEVELS: [1, 2, 3.5]` produce three tour columns that map to the Soundcast auto modes:

| Column               | Occupancy | Mode           |
|----------------------|-----------|----------------|
| `vehicle_occup_1`    | 1         | DRIVEALONEFREE (and DRIVE_TRN access) |
| `vehicle_occup_2`    | 2         | SHARED2FREE    |
| `vehicle_occup_3.5`  | 3.5       | SHARED3FREE    |

---

## 3. Files created

All in `soundcast/inputs/model/activitysim/configs/`:

| File | Purpose |
|------|---------|
| `vehicle_allocation.yaml` | Component settings — MNL, `OCCUPANCY_LEVELS [1, 2, 3.5]`, preprocessor + `vehicles` table |
| `vehicle_allocation.csv` | Utility spec — alternatives `veh_num1..veh_num4` + `non_hh_veh`; availability, BEV-range penalty, body/fuel/age ASCs, occupancy and vehicles-vs-drivers interactions |
| `vehicle_allocation_coefficients.csv` | Coefficient values |
| `vehicle_allocation_annotate_choosers_preprocessor.csv` | Derives per-alternative `age_*`, `body_type_*`, `fuel_type_*`, `Range_*`, and round-trip `tot_tour_dist` |

The spec, coefficients, and preprocessor were **adapted from `prototype_mtc_extended`** (see
assumptions §5).

## 4. Files modified

All in `soundcast/inputs/model/activitysim/configs/`:

| File | Change |
|------|--------|
| `settings.yaml` | Added `- vehicle_allocation` to the `models:` list (after `non_mandatory_tour_scheduling`, before `tour_mode_choice_simulate`). |
| `tour_mode_choice.yaml` | Added `vehicles` to the `preprocessor` **and** `nontour_preprocessor` `TABLES:` lists. |
| `tour_mode_choice_annotate_choosers_preprocessor.csv` | Appended derivation of `sov_veh_option`/`sr2_veh_option`/`sr3p_veh_option` (atwork subtours use the parent tour's vehicle) and the corresponding `sov_auto_op_cost`/`sr2_auto_op_cost`/`sr3p_auto_op_cost`, each with a fallback to `costPerMile`. |
| `annotate_tours_tour_mode_choice.csv` | Appended resolution of `selected_vehicle` from the chosen `tour_mode`; non-auto tours get none; atwork subtours inherit the parent tour's vehicle. |
| `tour_mode_choice.csv` | Replaced `costPerMile` with `df.sov_auto_op_cost` / `df.sr2_auto_op_cost` / `df.sr3p_auto_op_cost` in the operating-cost terms for DRIVEALONEFREE, SHARED2FREE, SHARED3FREE, and DRIVE_TRN (4 lines). |
| `trip_mode_choice.yaml` | Added `vehicles` to the `preprocessor` `TABLES:` list. |
| `trip_mode_choice_annotate_trips_preprocessor.csv` | Appended `selected_tour_vehicle` (from `tours.selected_vehicle`) and `auto_op_cost` (vehicle's `auto_operating_cost`, fallback to `costPerMile`). |
| `trip_mode_choice.csv` | Replaced `costPerMile` with `df.auto_op_cost` in the operating-cost terms for DRIVEALONEFREE, SHARED2FREE, SHARED3FREE, and DRIVE_TRN (outbound + inbound) — 5 lines. |

### Fallback behavior
Every operating-cost lookup falls back to the original `costPerMile` scalar when there is no
allocated household vehicle — i.e. for the `non_hh_veh` alternative, for non-auto tours/trips, and
for the destination-choice **logsum** (non-tour) choosers that have no `vehicle_occup_*` columns.
This guarantees utilities never become `NaN` and that anything without a real allocated vehicle
behaves exactly as before this change.

---

## 5. Assumptions

1. **Coefficients are transferred, not estimated.** `vehicle_allocation.csv` and
   `vehicle_allocation_coefficients.csv` are taken verbatim from `prototype_mtc_extended`. They are
   a functional starting point, **not** PSRC-estimated parameters. **Recalibration is expected.**
2. **Four household-vehicle alternatives** (`veh_num1..veh_num4`) plus one `non_hh_veh` option.
   Households owning 5+ vehicles cannot select the 5th+ for a tour (matches MTC behavior; rare).
3. **Units match.** The `vehicles.auto_operating_cost` values (~10.5–33.1 cents/mile in
   `vehicle_type_data_2026.csv`) are the same units as the flat `costPerMile: 18.29`, so the
   substitution is dimensionally consistent.
4. **Vehicle-type naming** is `Body_age_Fuel` (e.g. `Car_0_BEV`), which the preprocessor parses by
   splitting on `_` — body = token 0, age = token 1, fuel = token 2. This matches the Soundcast
   `vehicle_type_data` naming, so the MTC preprocessor works unchanged except for the skim below.
5. **BEV-range distance skim.** MTC's preprocessor used a `SOV_DIST` round-trip skim for the
   BEV-range term; Soundcast has no skim by that name, so it was changed to **`sov_inc1d`**
   (Soundcast's period-indexed SOV distance, income bin 1). *Flagged for a units/behavior sanity
   check.*
6. **DRIVE_TRN (drive-to-transit)** is treated as drive-alone vehicle usage → occupancy-1 vehicle
   (`sov_auto_op_cost`), consistent with the MTC treatment of drive-access legs.
7. **Atwork subtours** have no allocation of their own; they inherit the parent tour's
   `selected_vehicle`. If the parent did not use a household vehicle, the subtour has none and falls
   back to `costPerMile`.
8. **Shared-ride operating cost is not split by occupancy.** As in the pre-existing spec, the SR2/SR3
   operating-cost terms are not divided by `costShareSr2`/`costShareSr3` — that behavior was
   preserved; only the per-mile rate was swapped.

---

## 6. Validation (By Claude Code)

**Environment:** the runnable interpreter is the uv venv at `activitysim/.venv` (Python 3.10,
editable activitysim). It had to be rebuilt with `uv sync` (its Python had been deleted). Base
Anaconda (3.13) does **not** have activitysim.

**Run:** resumed the existing `asim_data_test` pipeline (~47k households) after
`non_mandatory_tour_scheduling` into a scratch output dir (production `asim_output` untouched):

```
<.venv python> -m activitysim run -c <configs> -d asim_data_test -o <out> -r vehicle_allocation
```
(run from a neutral working directory — running from the repo root shadows the installed
`activitysim` package with the local source folder).

**Validation date:** 2026-08-18.

**Bug found & fixed during validation:** the atwork parent-vehicle lookup in
`annotate_tours_tour_mode_choice.csv` must be guarded:
`reindex(df.selected_vehicle, df.parent_tour_id) if 'selected_vehicle' in df.columns else np.nan`.
Without the guard it `AttributeError`s on the first pass, because a target being built by
`assign()` is not yet a column/attribute of `df`. (This matches the MTC guard, which had been
dropped.)

**Result:** `vehicle_allocation → tour_mode_choice → atwork_subtour_mode_choice → trip_mode_choice
→ write_tables` all completed (exit 0). Output checks:

| Check | Result |
|-------|--------|
| Non-atwork non-auto tours wrongly assigned a vehicle | 0 |
| WALK tours holding a vehicle | 100% are atwork subtours inheriting a driving parent's car |
| Auto atwork subtours with a parent vehicle → match parent | 100% |
| Auto atwork subtours with no parent vehicle → also none | 100% |
| Distinct vehicle types feeding auto-tour operating cost | 425 |
| Operating-cost spread realized | 10.5–33.1 ¢/mi (vs the old flat 18.29) |
| Trips with a mode assigned | 220,092 / 220,092 |

---

## 7. Downstream dependency map (what relies on the vehicles fleet)

- **Direct (hard) dependency:** `vehicle_allocation` — reads the `vehicles` table
  (`vehicle_type`, `auto_operating_cost`, `Range`, and parsed body/fuel/age).
- **Indirect (through allocation):** `tour_mode_choice_simulate`, `atwork_subtour_mode_choice`,
  `trip_mode_choice` — read `vehicles.auto_operating_cost` keyed by the allocated vehicle.
- **Not dependent** (keyword matches are on `auto_ownership`, the vehicle *count*):
  `stop_frequency`, `disaggregate_accessibility`.
- **Decoupled:** Soundcast `emissions.py` and the standard summaries use MOVES rates + network VMT +
  total `auto_ownership`; they do **not** read `vehicle_type`/`fuel_type`. So the fleet's EV/fuel
  composition does not yet influence emissions.

---

## 8. Open items / recommended next steps

1. **Recalibrate** `vehicle_allocation` coefficients and re-check mode-choice calibration, since the
   operating-cost feedback shifts auto utilities.
2. **Verify the `sov_inc1d` distance** used for the BEV-range term (units and round-trip
   construction) — see assumption §5.
3. **Emissions integration (optional, larger effort):** if EV/fuel-type-sensitive emissions are a
   goal, `emissions.py` would need to route `selected_vehicle`/fuel type (and `co2gpm`) into the
   running-emissions calc; today the fleet composition never reaches the GHG numbers.
4. Consider whether SR2/SR3 operating cost should be split by occupancy (`costShareSr2/Sr3`) — see
   assumption §8.
