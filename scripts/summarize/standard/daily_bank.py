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
    if os.path.exists(to_dir):
        shutil.rmtree(to_dir)
    shutil.copytree(from_dir, to_dir)


def merge_networks(master_network, merge_network):
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
    """Extract link attribute values for a given scenario and emmebank (i.e., time period)"""

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
    project = state.main_project

    # Use a copy of an existing bank for the daily bank and rename
    copy_emmebank("Banks/7to8", "Banks/Daily")
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

    for tod, time_period in state.network_settings.sound_cast_net_dict.items():
        path = os.path.join("Banks", tod, "emmebank")
        bank = _emmebank.Emmebank(path)
        scenario = bank.scenario(1002)
        network = scenario.get_network()

        # Trip table data:
        for matrix in bank.matrices():
            if matrix.name in daily_matrix_dict:
                hourly_arr = matrix.get_numpy_data()
                daily_matrix_dict[matrix.name] = (
                    daily_matrix_dict[matrix.name] + hourly_arr
                )

        # Network data:
        if len(time_period_list) == 0:
            daily_network = network
            time_period_list.append(time_period)
        elif time_period not in time_period_list:
            time_period_list.append(time_period)  # this line was repeated below
            daily_network = merge_networks(daily_network, network)
            time_period_list.append(time_period)  # this line was repeated above
    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    # Write daily trip tables:
    for matrix in daily_emmebank.matrices():
        matrix.set_numpy_data(daily_matrix_dict[matrix.name])

    for extra_attribute in daily_scenario.extra_attributes():
        if extra_attribute not in ["@type"]:
            daily_scenario.delete_extra_attribute(extra_attribute)
    daily_volume_attr = daily_scenario.create_extra_attribute("LINK", "@tveh")
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
    attr_list = ["@tv" + x for x in state.network_settings.tods]

    for link in daily_network.links():
        for item in state.network_settings.tods:
            link["@tveh"] = link["@tveh"] + link["@v" + item]
    daily_scenario.publish_network(daily_network, resolve_attributes=True)

    # Write daily link-level results
    export_link_values(project)


if __name__ == "__main__":
    main()
