"""Daily bank creation and network summarization for Soundcast transportation model.

This module creates a daily Emme databank by aggregating time-of-day specific
transportation analysis results. It merges trip matrices and networks from
multiple time periods into a single daily representation for analysis.
"""

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

import inro.emme.database.emmebank as _emmebank
import os
from settings.data_wrangling import text_to_dictionary
import shutil
import pandas as pd


def copy_emmebank(from_dir, to_dir):
    """Copy an Emme databank directory from source to destination.
    
    Args:
        from_dir: Source directory path containing the Emme databank
        to_dir: Destination directory path for the copied databank
        
    Note:
        If destination directory exists, it will be removed first.
        Creates a complete copy of the Emme databank structure.
    """
    if os.path.exists(to_dir):
        shutil.rmtree(to_dir)
    shutil.copytree(from_dir, to_dir)


def merge_networks(master_network, merge_network):
    """Merge transportation network elements from one network into another.
    
    Args:
        master_network: Primary Emme network to receive merged elements
        merge_network: Source Emme network providing elements to merge
        
    Returns:
        Emme network: Updated master network with merged elements
        
    Note:
        Adds nodes and links from merge_network to master_network if they
        don't already exist. Preserves node coordinates and link modes.
    """
    for node in merge_network.nodes():
        if not master_network.node(node.id):
            new_node = master_network.create_regular_node(node.id)
            new_node.x = node.x
            new_node.y = node.y

    for link in merge_network.links():
        if not master_network.link(link.i_node, link.j_node):
            master_network.create_link(link.i_node, link.j_node, link.modes)

    return master_network


def export_link_values(project):
    """Extract and export link attribute values from Emme network.
    
    Args:
        project: Emme project instance containing the network scenario
        
    Note:
        Exports all link attributes to CSV file and creates network shapefile.
        Output files are saved in outputs/network/ directory for analysis.
        Reshapes data from wide to long format for easier analysis.
    """
    network = project.current_scenario.get_network()
    link_type = "LINK"

    # list of all link attributes
    link_attr = network.attributes(link_type)

    # Initialize a dataframe to store results
    df = pd.DataFrame()
    for attr in link_attr:
        # print("processing: " + str(attr))
        # store values and node id for a single attr in a temp df
        df_attr = pd.DataFrame(
            [
                network.get_attribute_values(link_type, [attr])[1].keys(),
                network.get_attribute_values(link_type, [attr])[1].values(),
            ]
        ).T
        df_attr.columns = ["nodes", "value"]
        df_attr["measure"] = str(attr)

        df = pd.concat([df, df_attr])

    # Lengthen tablewise
    df = df.pivot(index="nodes", columns="measure", values="value").reset_index()
    df.to_csv("outputs/network/daily_network_results.csv")

    # Export shapefile
    shapefile_dir = r"outputs/network/shapefile"
    if not os.path.exists(shapefile_dir):
        os.makedirs(shapefile_dir)
    network_to_shapefile = project.m.tool(
        "inro.emme.data.network.export_network_as_shapefile"
    )
    network_to_shapefile(export_path=shapefile_dir, scenario=project.current_scenario)


def main(state):
    """Create daily Emme databank by aggregating time-of-day results.
    
    Args:
        state: Configuration object containing model settings and project info
        
    Note:
        Creates a daily databank by:
        1. Adding time-of-day banks to main project
        2. Copying base bank structure for daily analysis
        3. Aggregating trip matrices across time periods
        4. Merging network elements from all time periods
        5. Calculating daily link volumes and attributes
        6. Exporting results to CSV and shapefile formats
    """
    project = state.main_project

    # Add banks to the main project if not already present
    project_bank_list = [
            database.title() for database in project.data_explorer.databases()
        ]
    for tod in state.network_settings.tods:
        if tod not in project_bank_list:
            project.data_explorer.add_database("Banks/" + tod + "/emmebank")
    project.desktop.project.save()
    state.main_project.change_active_database(state.network_settings.tods[0])

    # Use a copy of an existing bank for the daily bank and rename
    # if daily bank file doesn't already exist
    if not os.path.exists("Banks/Daily"):
        copy_emmebank(f"Banks/{state.network_settings.tods[1]}", "Banks/Daily")
    daily_emmebank = _emmebank.Emmebank(r"Banks/Daily/emmebank")
    daily_emmebank.title = "daily"
    daily_scenario = daily_emmebank.scenario(1002)
    daily_network = daily_scenario.get_network()

    database = project.data_explorer.add_database("Banks/Daily/emmebank")
    database.open()

    matrix_dict = text_to_dictionary("demand_matrix_dictionary", state.model_input_dir)
    uniqueMatrices = set(matrix_dict.values())

    # delete and create new matrices since this is a full copy of another time period
    for matrix in daily_emmebank.matrices():
        daily_emmebank.delete_matrix(matrix.id)

    for matrix in uniqueMatrices:
        daily_matrix = daily_emmebank.create_matrix(
            daily_emmebank.available_matrix_identifier("FULL")
        )
        daily_matrix.name = matrix

    daily_matrix_dict = {}
    for matrix in daily_emmebank.matrices():
        daily_arr = matrix.get_numpy_data()
        daily_matrix_dict[matrix.name] = daily_arr

    time_period_list = []

    daily_trips_df = pd.DataFrame()

    for tod, time_period in state.network_settings.sound_cast_net_dict.items():
        path = os.path.join("Banks", tod, "emmebank")
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        network = scenario.get_network()

        # Trip table data:
        results_dict = {}
        for matrix in bank.matrices():
            if matrix.name in daily_matrix_dict:
                hourly_arr = matrix.get_numpy_data()
                daily_matrix_dict[matrix.name] = (
                    daily_matrix_dict[matrix.name] + hourly_arr
                )
                results_dict[str(matrix.name)] = hourly_arr.sum()
        df = pd.DataFrame(results_dict.values(), index=results_dict.keys())
        df['tod'] = tod
        daily_trips_df = pd.concat([daily_trips_df, df])

        # Network data:
        if len(time_period_list) == 0:
            daily_network = network
            time_period_list.append(time_period)
        elif time_period not in time_period_list:
            time_period_list.append(time_period)  # this line was repeated below
            daily_network = merge_networks(daily_network, network)
            time_period_list.append(time_period)  # this line was repeated above
    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    daily_trips_df.columns = ['trips','tod']
    daily_trips_df.to_csv('outputs/trips_by_class.csv')

    # Write daily trip tables:
    for matrix in daily_emmebank.matrices():
        matrix.set_numpy_data(daily_matrix_dict[matrix.name])

    for extra_attribute in daily_scenario.extra_attributes():
        if extra_attribute not in ["@type"]:
            daily_scenario.delete_extra_attribute(extra_attribute)
    daily_scenario.create_extra_attribute("LINK", "@tveh")
    daily_network = daily_scenario.get_network()

    for tod, time_period in state.network_settings.sound_cast_net_dict.items():
        path = os.path.join("Banks", tod, "emmebank")
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        network = scenario.get_network()
        if daily_scenario.extra_attribute("@v" + tod):
            daily_scenario.delete_extra_attribute("@v" + tod)
        attr = daily_scenario.create_extra_attribute("LINK", "@v" + tod)
        values = scenario.get_attribute_values("LINK", ["@tveh"])
        daily_scenario.set_attribute_values("LINK", [attr], values)

    daily_network = daily_scenario.get_network()

    for link in daily_network.links():
        for item in state.network_settings.tods:
            link["@tveh"] = link["@tveh"] + link["@v" + item]
    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    # Write daily link-level results
    export_link_values(project)


if __name__ == "__main__":
    main()
