#############################
# Path-Based Assignment Spec
#############################

assignment_spec = {
        "type": "PATH_BASED_TRAFFIC_ASSIGNMENT",
        "classes": [],
        "performance_settings": {
            "max_path_memory": 3000,
            "gap_computation_freq": 5,
            "path_cost_equality_tolerance": {
                "initial_proportion": 0.001,
                "refinement_iteration": 30,
                "refined_proportion": 0.00001
            }
        },
        "background_traffic": None,
        "stopping_criteria": {
            "max_iterations": 10,
            "best_relative_gap": 0.01,
            "relative_gap": 0.0001,
            "normalized_gap": 0.01
        }
    }

assignment_spec_class = {
        "mode": "",
        "demand": "",
        "generalized_cost": {
            "link_costs": "",
            "perception_factor": ""
        }
    },

#############################
# Traffic Analysis Spec
#############################

attribute_based_skim_spec = {
       "type":"PATH_BASED_TRAFFIC_ANALYSIS",
       "classes":[],
       "path_analysis":{
          "link_component":"length",
          "turn_component": None, 
          "operator":"+",
          "selection_threshold":{
             "lower":0,
             "upper":999999
          },
          "path_to_od_composition":{
             "considered_paths":"ALL",
             "operator":"average"
          }
       },
       "cutoff_analysis": None 
    }

attribute_based_skim_spec_class = {
         "results":{
            "od_travel_times":{
               "shortest_paths": None
            },
            "link_volumes": None,
            "turn_volumes": None
         },
         "analysis":{
            "results":{
               "selected_link_volumes": None,
               "selected_turn_volumes": None,
               "od_values": None
            }
         }
      },

#############################
# Path-Based Volume
#############################

volume_spec = {
    "type": "PATH_BASED_TRAFFIC_ANALYSIS",
    "classes": [],
    "path_analysis": {
        "link_component": "length",
        "turn_component": None,
        "operator": "+",
        "selection_threshold": {
            "lower": 0,
            "upper": 999999
        },
        "path_to_od_composition": {
            "considered_paths": "ALL",
            "operator": "average"
        }
    },
    "cutoff_analysis": None
}

volume_spec_class = {
            "results": {
                "od_travel_times": None,
                "link_volumes": None,
                "turn_volumes": None
            },
            "analysis": {
                "results": {
                    "selected_link_volumes": None,
                    "selected_turn_volumes": None,
                    "od_values": None
                }
            }
        },

#############################
# Generalized Cost
#############################

generalized_cost_spec = {
    "type": "PATH_BASED_TRAFFIC_ANALYSIS",
    "classes": [],
    "path_analysis": {
        "link_component": "length",
        "turn_component": None,
        "operator": "+",
        "selection_threshold": {
            "lower": 0,
            "upper": 999999
        },
        "path_to_od_composition": {
            "considered_paths": "ALL",
            "operator": "average"
        }
    },
    "cutoff_analysis": None
}

generalized_cost_spec_class = {
            "results": {
                "od_travel_times": None,
                "link_volumes": None,
                "turn_volumes": None
            },
            "analysis": {
                "results": {
                    "selected_link_volumes": None,
                    "selected_turn_volumes": None,
                    "od_values": None
                }
            }
        },