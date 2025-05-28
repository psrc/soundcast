# Copyright [2014] [Puget Sound Regional Council]

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys, datetime, re
import subprocess
import inro.emme.desktop.app as app
import json
import shutil, errno
from shutil import copy2 as shcopy
import inro.emme.database.emmebank as _eb
import random
import h5py
import pandas as pd
from pathlib import Path

sys.path.append(os.path.join(os.getcwd(), "inputs", "model", "skim_parameters"))
sys.path.append(os.getcwd())
from logcontroller import *

# from emme_configuration import *
from skimming.skim_templates import *

# from settings import state
# import input_configuration
import glob
import toml

# state = state.generate_state(run_args.args.configs_dir)

# config = toml.load(os.path.join(os.getcwd(), "configuration/input_configuration.toml"))
# emme_config = toml.load(
#     os.path.join(os.getcwd(), "configuration/emme_configuration.toml")
# )
# network_config = toml.load(
#     os.path.join(os.getcwd(), "configuration/network_configuration.toml")
# )


def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text


@timed
def copy_daysim_code():
    print("Copying Daysim executables...")
    if not os.path.exists(os.path.join(os.getcwd(), "daysim")):
        os.makedirs(os.path.join(os.getcwd(), "daysim"))
    try:
        dir_util.copy_tree(daysim_code, "daysim")
    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        sys.exit(1)


@timed
def copy_seed_skims(state):
    print(
        "You have decided to start your run by copying seed skims that Daysim will use on the first iteration. Interesting choice! This will probably take around 15 minutes because the files are big. Starting now..."
    )
    if not (os.path.isdir(scenario_inputs + "/seed_skims")):
        print(
            "It looks like you do not hava directory called"
            + scenario_inputs
            + "/seed_skims, where the code is expecting the files to be. Please make sure to put your seed_skims there."
        )
    for filename in glob.glob(os.path.join(scenario_inputs + "/seed_skims", "*.*")):
        shutil.copy(filename, "inputs")
    print("Done copying seed skims.")


def text_to_dictionary(dict_name, model_inputs_dir, subdir=""):
    """
    Import text file as dictionary. Data must be in dictionary format.
    e.g., key: value
    """

    input_filename = model_inputs_dir / f"skim_parameters/{subdir}/{dict_name}.txt"
    my_file = open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(":")
        my_dictionary[eval(k)] = v.strip()

    return my_dictionary


def json_to_dictionary(dict_name, model_inputs_dir, subdir=""):
    """
    Import JSON-formatted input as dictionary. Expects file extension .json.
    """

    input_filename = model_inputs_dir / f"skim_parameters/{subdir}/{dict_name}.json"
    my_dictionary = json.load(open(input_filename))

    return my_dictionary


@timed
def setup_emme_bank_folders(state):
    """Generate folder and empty emmebanks for each time of day period."""

    # tod_dict = text_to_dictionary("time_of_day", "lookup")
    emmebank_dimensions_dict = json_to_dictionary(
        "emme_bank_dimensions", state.model_input_dir
    )

    # Remove and existing banks
    if not os.path.exists("Banks"):
        os.makedirs("Banks")
    else:
        shutil.rmtree("Banks")

    time_periods = state.network_settings.tods.copy()
    time_periods.append("TruckModel")
    time_periods.append("Supplementals")
    for period in time_periods:
        print("Creating bank for time period: " + period)
        os.makedirs(os.path.join("Banks", period))
        path = os.path.join("Banks", period, "emmebank")
        emmebank = _eb.create(path, emmebank_dimensions_dict)
        emmebank.title = period
        emmebank.unit_of_length = state.network_settings.unit_of_length
        emmebank.coord_unit_length = state.network_settings.coord_unit_length
        scenario = emmebank.create_scenario(1002)
        network = scenario.get_network()
        # At least one mode required per scenario. Other modes are imported in network_importer.py
        network.create_mode("AUTO", "a")
        scenario.publish_network(network)
        emmebank.dispose()


@timed
def setup_emme_project_folders(state):
    """Create Emme project folders for all time of day periods."""

    emme_toolbox_path = os.path.join(os.environ["EMMEPATH"], "toolboxes")
    # tod_dict = text_to_dictionary("time_of_day", "lookup")
    tod_list = state.network_settings.tods.copy()

    if os.path.exists(os.path.join("projects")):
        shutil.rmtree("projects")

    # Create time of day projects, associate with emmebank

    for tod in tod_list:
        project = app.create_project("projects", tod)
        desktop = app.start_dedicated(False, "cth", project)
        data_explorer = desktop.data_explorer()
        database = data_explorer.add_database("Banks/" + tod + "/emmebank")
        database.open()
        desktop.project.save()
        desktop.close()
        shcopy(emme_toolbox_path + "/standard.mtbx", os.path.join("projects", tod))

    # Create master project, associate with all emmebanks by time of day
    project = app.create_project("projects", state.main_project_name)
    desktop = app.start_dedicated(False, "psrc", project)
    data_explorer = desktop.data_explorer()
    tod_list.append("TruckModel")
    tod_list.append("Supplementals")

    for tod in tod_list:
        database = data_explorer.add_database("Banks/" + tod + "/emmebank")

    # Open the last database added so that there is an active one
    database.open()
    desktop.project.save()
    desktop.close()
    shcopy(
        emme_toolbox_path + "/standard.mtbx",
        os.path.join("projects", state.main_project_name),
    )


@timed
def copy_scenario_inputs(state):
    # Clear existing base_year and scenario folders
    for path in ["inputs/base_year", "inputs/scenario", "inputs/db"]:
        if os.path.exists(os.path.join(os.getcwd(), path)):
            shutil.rmtree(os.path.join(os.getcwd(), path), ignore_errors=True)

    # Copy base_year folder from inputs directory
    copyanything(
        Path(state.input_settings.soundcast_inputs_dir)
        / "base_year"
        / state.input_settings.base_year,
        "inputs/base_year",
    )

    # Copy network, landuse, and general (year-based) inputs
    copyanything(
        Path(state.input_settings.soundcast_inputs_dir) 
        / "db" 
        / state.input_settings.db_name, 
        Path("inputs/db") 
        / state.input_settings.db_name)
    copyanything(
        Path(state.input_settings.soundcast_inputs_dir)
        / "landuse"
        / state.input_settings.model_year
        / state.input_settings.landuse_inputs,
        "inputs/scenario/landuse",
    )
    copyanything(
        Path(state.input_settings.soundcast_inputs_dir)
        / "networks"
        / state.input_settings.model_year
        / state.input_settings.network_inputs,
        "inputs/scenario/networks",
    )


@timed
def copy_shadow_price_file():
    print("Copying shadow price file.")
    if not os.path.exists("working"):
        os.makedirs("working")
    shcopy(base_inputs + "/shadow_prices/shadow_prices.txt", "working")


@timed
def clean_up():
    delete_files = [
        "working\\household.bin",
        "working\\household.pk",
        "working\\parcel.bin",
        "working\\parcel.pk",
        "working\\parcel_node.bin",
        "working\\parcel_node.pk",
        "working\\park_and_ride.bin",
        "working\\park_and_ride_node.pk",
        "working\\person.bin",
        "working\\person.pk",
        "working\\zone.bin",
        "working\\zone.pk",
    ]

    for file in delete_files:
        if os.path.isfile(os.path.join(os.getcwd(), file)):
            os.remove(os.path.join(os.getcwd(), file))
        else:
            print(file)


@timed
def copy_accessibility_files(state):
    if state.input_settings.run_integrated:
        import_integrated_inputs()
    else:
        if not os.path.exists("inputs/scenario/landuse"):
            os.makedirs("inputs/scenario/landuse")

        file_dict = {
            os.path.join(
                state.input_settings.soundcast_inputs_dir,
                "landuse",
                state.input_settings.model_year,
                state.input_settings.landuse_inputs,
                "parcels_urbansim.txt",
            ): "inputs/scenario/landuse",
        }

        for src_file, dest_dir in file_dict.items():
            try:
                shcopy(src_file, dest_dir)
            except:
                print("error copying accessibility file: " + src_file)
                sys.exit(1)


def build_output_dirs():
    for path in [
        "outputs",
        r"outputs/daysim",
        "outputs/bike",
        "outputs/network",
        "outputs/transit",
        "outputs/landuse",
        "outputs/emissions",
        r"outputs/trucks",
        "outputs/supplemental",
    ]:
        if not os.path.exists(path):
            os.makedirs(path)


def import_integrated_inputs(state):
    """
    Convert Urbansim input file into separate files:
    - parcels_urbansim.txt
    - hh_and_persons.h5
    """

    print("Importing land use files from urbansim...")

    # Copy soundcast inputs and separate input files
    h5_inputs_dir = os.path.join(
        state.emme_settings.urbansim_outputs_dir,
        state.input_settings.model_year,
        "soundcast_inputs.h5",
    )
    shcopy(h5_inputs_dir, r"inputs/scenario/landuse/hh_and_persons.h5")

    h5_inputs = h5_inputs = h5py.File("inputs/scenario/landuse/hh_and_persons.h5")

    # Export parcels file as a txt file input
    parcels = pd.DataFrame()
    for col in h5_inputs["parcels"].keys():
        parcels[col] = h5_inputs["parcels"][col][:]

    parcels.to_csv(
        r"inputs/scenario/landuse/parcels_urbansim.txt", sep=" ", index=False
    )

    # Delete parcels group
    del h5_inputs["parcels"]


def update_skim_parameters(state):
    """
    Generate skim parameter spec files from templates.
    """

    # Based on toggles from input_configuration, remove modes if not used
    # from user_class and demand matrix list in skim_parameters input folder.

    keywords = []
    if not state.input_settings.include_av:
        keywords.append("av_")
    if not state.input_settings.include_tnc:
        keywords.append("tnc_")
    if not state.input_settings.include_delivery:
        keywords.append("delivery_")

    root_path = os.path.join(
        os.getcwd(), f"inputs/model/{state.input_settings.abm_model}/skim_parameters"
    )

    # Remove unused modes from user_classes and demand_matrix_dictionary
    for filename, ext in {
        "user_classes": "json",
        "demand_matrix_dictionary": "txt",
    }.items():
        template_path = os.path.join(
            root_path, "templates", filename + "_template." + ext
        )
        new_file_path = os.path.join(root_path, filename + "." + ext)
        with open(template_path) as template_file, open(new_file_path, "w") as newfile:
            for line in template_file:
                if not any(keyword in line for keyword in keywords):
                    newfile.write(line)

    #############################
    # Path-Based Traffic Assignment Spec
    #############################

    # Create an empty assignment dictionary with number of assignment classes from user_class
    user_class = json.load(open(os.path.join(root_path, "user_classes.json")))
    uc_count = len(user_class["Highway"])

    # Generate a dictionary for each user class to be assigned
    assignment_spec["classes"] = assignment_spec_class * uc_count

    # Fill in each user class with mode, name, toll, and perception factor
    for i in range(len(user_class["Highway"])):
        # Add this mode to the spec file
        my_group = user_class["Highway"][i]
        assignment_spec["classes"][0]["mode"] = my_group["Mode"]
        assignment_spec["classes"][0]["demand"] = my_group["Name"]
        assignment_spec["classes"][0]["generalized_cost"]["link_costs"] = my_group[
            "Toll"
        ]
        # assuming perception factor == 1 for all modes
        assignment_spec["classes"][0]["generalized_cost"]["perception_factor"] = 1.0

    # Write spec to file to be used in assignment in SkimsAndPaths.py
    with open(
        os.path.join(root_path, "auto", "path_based_assignment.json"), "w"
    ) as file:
        file.write(json.dumps(assignment_spec, indent=4, sort_keys=True))

    #############################
    # Attribute-Base Skim
    #############################

    # Generate a dictionary for each user class to be assigned
    attribute_based_skim_spec["classes"] = attribute_based_skim_spec_class * uc_count

    with open(
        os.path.join(root_path, "auto", "attribute_based_skim.json"), "w"
    ) as file:
        file.write(json.dumps(attribute_based_skim_spec, indent=4, sort_keys=True))

    #############################
    # Path-Based Volume
    #############################

    # Generate a dictionary for each user class to be assigned
    volume_spec["classes"] = volume_spec_class * uc_count

    with open(os.path.join(root_path, "auto", "path_based_volume.json"), "w") as file:
        file.write(json.dumps(volume_spec, indent=4, sort_keys=True))

    #############################
    # Generalized Cost
    #############################

    # Generate a dictionary for each user class to be assigned
    generalized_cost_spec["classes"] = generalized_cost_spec_class * uc_count

    with open(
        os.path.join(root_path, "auto", "path_based_generalized_cost.json"), "w"
    ) as file:
        file.write(json.dumps(generalized_cost_spec, indent=4, sort_keys=True))


def update_daysim_modes(state):
    """
    Apply settings in input_configuration to daysim_configuration and roster files:

    config['include_tnc']: PaidRideShareModeIsAvailable,
    config['include_av']: AV_IncludeAutoTypeChoice,
    config['tnc_av']: AV_PaidRideShareModeUsesAVs
    """

    # Store values from input_configuration in a dictionary:
    av_settings = ["include_av", "include_tnc", "tnc_av"]

    daysim_dict = {
        "AV_IncludeAutoTypeChoice": "include_av",
        "AV_UseSeparateAVSkimMatricesByOccupancy": "include_av",  # Must be updated or causes issues with roster
        "PaidRideShareModeIsAvailable": "include_tnc",
        "AV_PaidRideShareModeUsesAVs": "tnc_av",
    }

    mode_config_dict = {}
    for setting in av_settings:
        mode_config_dict[setting] = getattr(state.input_settings, setting)

    # Copy temp file to use
    daysim_config_path = os.path.join(
        os.getcwd(), "daysim_configuration_template.properties"
    )
    new_file_path = os.path.join(
        os.getcwd(), "daysim_configuration_template_tmp.properties"
    )

    with open(daysim_config_path) as template_file, open(new_file_path, "w") as newfile:
        for line in template_file:
            if any(value in line for value in daysim_dict.keys()):
                var = line.split(" = ")[0]
                line = (
                    var + " = " + str(mode_config_dict[daysim_dict[var]]).lower() + "\n"
                )
                newfile.write(line)
            else:
                newfile.write(line)

    # Replace the original daysim_configuration_template file with the updated version
    try:
        os.remove(daysim_config_path)
        os.rename(new_file_path, daysim_config_path)
    except OSError as e:  ## if failed, report it back to the user ##
        print("Error: " + e.filename + " - " + e.strerror)

    # Write Daysim roster and roster-combination files from template
    # Exclude AV alternatives if not included in scenario

    df = pd.read_csv(
        f"inputs/model/{state.input_settings.abm_model}/roster/templates/psrc_roster_template.csv"
    )
    if not state.input_settings.include_av:  # Remove TNC from mode list
        df = df[-df["mode"].isin(["av1", "av2", "av3"])]
    if (
        not state.input_settings.include_tnc_to_transit
    ):  # remove TNC-to-transit from potential path types
        df = df[
            -df["path-type"].isin(
                filter(lambda x: "tnc" in x, df["path-type"].unique())
            )
        ]
    if not state.input_settings.include_knr_to_transit:
        df = df[
            -df["path-type"].isin(
                filter(lambda x: "knr" in x, df["path-type"].unique())
            )
        ]
    df.fillna("null").to_csv(
        f"inputs/model/{state.input_settings.abm_model}/roster/psrc_roster.csv",
        index=False,
    )

    df = pd.read_csv(
        f"inputs/model/{state.input_settings.abm_model}/roster/templates/psrc-roster.combinations_template.csv",
        index_col="#",
        dtype=str
    )
    if not state.input_settings.include_av:
        df[["av1", "av2", "av3"]] = "FALSE"
    if not state.input_settings.include_tnc:
        df.loc[df.index[["tnc" in i for i in df.index]], "transit"] = "FALSE"
    # Adjust KNR path types
    if not state.input_settings.include_knr_to_transit:
        df.loc[["ferry-knr"], "transit"] = "FALSE"
    if not state.input_settings.include_tnc_to_transit:
        df.loc[["local-bus-tnc", "light-rail-tnc"], "transit"] = "FALSE"
    df.to_csv(
        f"inputs/model/{state.input_settings.abm_model}/roster/psrc-roster.combinations.csv"
    )


def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc:  # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else:
            raise
