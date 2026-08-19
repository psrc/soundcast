"""
Workplace location calibration helper functions.

Notes:
    The lru_cache decorator to ensure that survey data is loaded and computed only once per Python process.
    Context is developed in _build_expression_context() in activitysim.core.calibration.
"""

import matplotlib.pyplot as plt
import pandas as pd
import os
from functools import lru_cache

# Use uncloned survey data for household and person level models
SURVEY_DATA_FOLDER = "R:/e2projects_two/2023_base_year/2023_survey/activitysim_format_20260629/skims_attached/uncloned"


def compute_distances(context, origins, destinations):
    # Compute distances between origins and destinations using the network level of service
    # using non-time-dependent DIST skim
    distances = context["skim_dict"].lookup(
        origins, destinations, "DIST"
    )
    # time dependent example
    # distances = skim_dict.lookup_3d(origins, destinations, 'AM', 'SOV_DIST')
    return distances


# @lru_cache(maxsize=1)
def _survey_persons() -> pd.DataFrame:
    """Load survey persons once per Python process."""
    return pd.read_csv(os.path.join(SURVEY_DATA_FOLDER, "survey_persons.csv"))

# @lru_cache(maxsize=1)
def _survey_households() -> pd.DataFrame:
    """Load survey households once per Python process."""
    return pd.read_csv(os.path.join(SURVEY_DATA_FOLDER, "survey_households.csv"))


# @lru_cache(maxsize=1)
def _survey_worker_distances(context):
    """Compute survey worker distances once and reuse across calibration rows."""
    survey_persons = _survey_persons()
    survey_workers = survey_persons[survey_persons["workplace_zone_id"] > 0].copy()

    # Exclude work from home
    survey_workers = survey_workers[survey_workers["workplace_zone_id"] != survey_workers["home_maz"]]

    survey_households = _survey_households().set_index("household_id")
    survey_workers["hh_weight"] = survey_workers["household_id"].map(
        survey_households["hh_weight"]
    )

    survey_home_zone_ids = survey_workers["household_id"].map(
        survey_households["home_zone_id"]

    )
    # land_use = context["land_use"]
    # taz_lookup = pd.Series(land_use.TAZ, index=land_use.index)

    # survey_home_zone_ids = survey_home_zone_ids.map(taz_lookup).astype("int")
    # survey_workplace_zone_ids = (
    #     survey_workers["workplace_zone_id"].map(taz_lookup)
    # ).astype("int")
    survey_workplace_zone_ids = survey_workers["workplace_zone_id"]

    distances = compute_distances(context, survey_home_zone_ids, survey_workplace_zone_ids)
    survey_workers["distance"] = distances
    return survey_workers


def summarize_model(context, min_dist=1, max_dist=2):
    """Summarize the model results for workplaces within the specified distance range."""
    persons = context["persons"]
    workers = persons[persons["workplace_zone_id"] > 0]
    home_zone_ids = workers["home_zone_id"]
    workplace_zone_ids = workers["workplace_zone_id"]

    # land_use = context["land_use"]
    # taz_lookup = pd.Series(land_use.TAZ, index=land_use.index)

    # home_zone_ids = home_zone_ids.map(taz_lookup)
    # workplace_zone_ids = workplace_zone_ids.map(taz_lookup)

    distances = compute_distances(context, home_zone_ids, workplace_zone_ids)

    # Filter distances within the specified range
    mask = (distances >= min_dist) & (distances < max_dist)
    filtered_distances = distances[mask]

    share = len(filtered_distances) / len(distances) if len(distances) > 0 else 0
    return share


def summarize_survey(context, min_dist=1, max_dist=2):
    """Summarize the survey results for workplaces within the specified distance range."""

    survey_workers = _survey_worker_distances(context)
    if survey_workers.empty:
        return 0

    mask = (survey_workers["distance"] >= min_dist) & (
        survey_workers["distance"] < max_dist
    )
    total_weight = survey_workers["hh_weight"].sum()
    if total_weight == 0:
        return 0

    weighted_share = survey_workers.loc[mask, "hh_weight"].sum() / total_weight
    return weighted_share


def report_workplace_location(context):
    """Workplace location distance frequency plot comparing model results with observed data."""
    print("summarizing workplace location model")
    model_persons = context["persons"]
    model_workers = model_persons[model_persons["workplace_zone_id"] > 0]
    model_home_zone_ids = model_workers["home_zone_id"]
    model_workplace_zone_ids = model_workers["workplace_zone_id"]

    model_distances = compute_distances(
        context, model_home_zone_ids, model_workplace_zone_ids
    )

    survey_distances = _survey_worker_distances(context)

    # Here you can add code to compare model_distances and survey_distances,
    # for example by plotting histograms or computing summary statistics.
    plt.hist(model_distances, bins=20, density=True, alpha=0.5, label="Model")
    plt.hist(survey_distances["distance"], bins=20, density=True, alpha=0.5, label="Survey")
    plt.xlabel("Distance")
    plt.ylabel("Frequency")
    plt.legend()
    # component_output_dir set in the evaluation context
    plt.savefig(
        os.path.join(
            context["component_output_dir"], "workplace_location_comparison.png"
        )
    )
    plt.close()
