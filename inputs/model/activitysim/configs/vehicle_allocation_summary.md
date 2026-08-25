# Vehicle Allocation — Summary

**Date:** 2026-08-18 · **Model:** Soundcast / ActivitySim
Full details: `VEHICLE_ALLOCATION.md` (same directory)

## What
Added the `vehicle_allocation` component after `vehicle_type_choice`, and wired its output into
tour + trip mode choice. The **selected vehicle's `auto_operating_cost`** now drives the auto
operating-cost terms, replacing the flat scalar `costPerMile = 18.29` (cents/mile). This is the
first model that actually uses `vehicle_type_choice` output.

Pipeline: `vehicle_type_choice → vehicle_allocation → tour_mode_choice / trip_mode_choice`.
Occupancy levels `[1, 2, 3.5]` map to DRIVEALONEFREE / SHARED2FREE / SHARED3FREE.

## Files
**Created (configs/):** `vehicle_allocation.yaml`, `vehicle_allocation.csv`,
`vehicle_allocation_coefficients.csv`, `vehicle_allocation_annotate_choosers_preprocessor.csv`

**Modified (configs/):** `settings.yaml` (added step), `tour_mode_choice.yaml` +
`trip_mode_choice.yaml` (added `vehicles` table), `tour_mode_choice_annotate_choosers_preprocessor.csv`,
`annotate_tours_tour_mode_choice.csv`, `trip_mode_choice_annotate_trips_preprocessor.csv`
(derive per-vehicle op cost + `selected_vehicle`), and `tour_mode_choice.csv` +
`trip_mode_choice.csv` (swapped `costPerMile` → allocated-vehicle cost). Falls back to `costPerMile`
for non-household vehicles / non-auto / logsum choosers.

## Key assumptions
- Spec + coefficients **transferred verbatim from prototype_mtc_extended** — not locally estimated;
  **recalibration expected** and mode choice will shift.
- 4 household-vehicle alternatives + `non_hh_veh`.
- `auto_operating_cost` units (cents/mile) match the old `costPerMile` scalar.
- BEV-range term uses `sov_inc1d` (Soundcast) in place of MTC's `SOV_DIST` — **verify units**.
- Atwork subtours inherit the parent tour's vehicle.

## Validation
Rebuilt the `activitysim/.venv`, resumed `asim_data_test` (~47k hh) after
`non_mandatory_tour_scheduling`. Fixed one bug (missing `if 'selected_vehicle' in df.columns` guard
on the atwork parent lookup). Full chain ran to `write_tables` (exit 0). Checks: 0 non-auto tours
mis-assigned a vehicle; atwork inheritance 100%; 425 vehicle types feeding cost; op-cost spread
10.5–33.1 ¢/mi vs the old flat 18.29.

## Open items
Recalibrate; verify `sov_inc1d` units; emissions/summaries are **decoupled** (MOVES + network VMT,
no fuel type) so fleet composition doesn't yet affect GHG — a separate effort if wanted.
