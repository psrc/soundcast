import matplotlib.pyplot as plt
import pandas as pd
import os

# Use uncloned survey data for household and person level models
SURVEY_DATA_FOLDER = "R:/e2projects_two/2023_base_year/2023_survey/activitysim_format_20260629/skims_attached/uncloned"


# @lru_cache(maxsize=1)
def _survey_households() -> pd.DataFrame:
    """Load survey households once per Python process."""
    return pd.read_csv(os.path.join(SURVEY_DATA_FOLDER, "survey_households.csv"))


def summarize_model(context, filter):
    """Calculate shares for filtered data"""
    households = context["households"]
    households = households[filter]
    share = len(households) / len(context["households"]) if len(context["households"]) > 0 else 0

    return share

def summarize_survey(context, filter):
    """Summarize the survey results for workplaces within the specified distance range."""

    households = _survey_households()
    households = households[filter]
    share = len(households) / len(context["households"]) if len(context["households"]) > 0 else 0

    return share
    
def report_auto_ownership(context):
    model_hhs = context["households"]
    survey_hhs = pd.read_csv(
        os.path.join(SURVEY_DATA_FOLDER, "survey_households.csv")
    )

    model_summary = (
        model_hhs.auto_ownership.value_counts(normalize=True).sort_index().fillna(0)
    )

    survey_total_weight = survey_hhs["hh_weight"].sum()
    survey_hhs['auto_ownership'] = survey_hhs['auto_ownership'].clip(upper=4)
    survey_summary = (
        survey_hhs.groupby("auto_ownership", dropna=False)["hh_weight"]
        .sum()
        .div(survey_total_weight)
        .sort_index()
        .fillna(0)
        .rename("weighted_dist")
    )
    summary_df = (
        pd.DataFrame({"model": model_summary, "survey": survey_summary})
        .reset_index()
        .rename(columns={"index": "num_autos"})
    )

    # plot comparing model and survey distributions
    summary_df.plot(x="auto_ownership", y=["model", "survey"], kind="bar")
    plt.title("Auto Ownership Distribution: Model vs Survey")
    plt.xlabel("Number of Autos")
    plt.ylabel("Proportion of Households")
    plt.legend(title="Data Source")
    plt.savefig(
        os.path.join(context["component_output_dir"], "auto_ownership_comparison.png")
    )
    plt.close()