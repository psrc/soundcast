import pandas as pd
import matplotlib.pyplot as plt
import os

# Use cloned survey data for trip/tour
SURVEY_DATA_FOLDER = "R:/e2projects_two/2023_base_year/2023_survey/activitysim_format_20260629/skims_attached"


TOUR_MODE_GROUPS = {
    "DRIVEALONEFREE": ("DRIVEALONEFREE",),
    "SHARED2FREE": ("SHARED2FREE",),
    "SHARED3FREE": ("SHARED3FREE",),
    "WALK": ("WALK",),
    "ALL_TRANSIT": ("WALK_LOC", "WALK_LR", "WALK_FRY", "WALK_COM", "DRIVE_TRN"),
    "SCH_BUS": ("SCH_BUS",),
    "BIKE": ("BIKE",),
    "TNC": ("TNC",),
}
MODEL_TOUR_MODES = tuple(mode for modes in TOUR_MODE_GROUPS.values() for mode in modes)


def summarize_model(context, mode_group, vehicle_group):
    """Summarize a model mode share for a mutually exclusive vehicle-availability group."""
    tours = context["tours"]
    households = context["households"]

    autos = households["auto_ownership"]
    workers = households["num_workers"]
    if vehicle_group == "zero_auto":
        household_mask = autos == 0
    elif vehicle_group == "auto_insuff":
        household_mask = (autos > 0) & (autos < workers)
    elif vehicle_group == "auto_suff":
        household_mask = (autos > 0) & (autos >= workers)
    else:
        raise ValueError(f"Unknown vehicle group: {vehicle_group}")

    if mode_group not in TOUR_MODE_GROUPS:
        raise ValueError(f"Unknown tour mode group: {mode_group}")

    household_ids = households.index[household_mask]
    grouped_tours = tours.loc[tours["household_id"].isin(household_ids)]
    modeled_tours = grouped_tours.loc[grouped_tours["tour_mode"].isin(MODEL_TOUR_MODES)]
    if modeled_tours.empty:
        raise ValueError(f"No modeled tours found for vehicle group: {vehicle_group}")

    matching_modes = TOUR_MODE_GROUPS[mode_group]
    return float(modeled_tours["tour_mode"].isin(matching_modes).sum() / len(modeled_tours))


def report_tour_mode_choice(context):
    model_tours = context["tours"]
    survey_tours = None
    survey_tours = pd.read_csv(os.path.join(SURVEY_DATA_FOLDER, "survey_tours.csv"))

    model_summary = (
        model_tours.tour_mode.value_counts(normalize=True).sort_index().fillna(0)
    )
    if "tour_weight" in survey_tours.columns:
        survey_summary = survey_tours.groupby("tour_mode").tour_weight.sum()
        survey_summary = survey_summary / survey_tours.tour_weight.sum()
    else:
        survey_summary = survey_tours.groupby("tour_mode").size()

    summary_df = (
        pd.DataFrame({"model": model_summary, "survey": survey_summary})
        .reset_index()
        .rename(columns={"index": "tour_mode"})
    )

    # plot comparing model and survey distributions
    summary_df.plot(x="tour_mode", y=["model", "survey"], kind="bar")
    plt.title("Tour Mode Choice Distribution: Model vs Survey")
    plt.xlabel("Tour Mode")
    plt.ylabel("Proportion of Tours")
    plt.legend(title="Data Source")
    plt.savefig(
        os.path.join(context["component_output_dir"], "tour_mode_choice_comparison.png")
    )
    plt.close()
