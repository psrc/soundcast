class TOD_Parameters (object):
    def __init__(self, network_config, tod):
        self.network_config = network_config
        self.tod = tod
        self.skim_distance = self._skim_for_distance()
        self.skim_generalized_cost = self._skim_generalized_cost()
        self.skim_bike_walk = self._skim_for_bike_walk()
        self.skim_types = self._skim_types()
        self.run_transit = self._run_transit()

    def _skim_for_distance(self):
        return self.tod in self.network_config['distance_skim_tod']
    
    def _skim_generalized_cost(self):
        return self.tod in self.network_config['generalized_cost_tod']
    
    
    def _skim_for_bike_walk(self):
        return self.tod in self.network_config['bike_walk_skim_tod']
        
    def _skim_types(self):
        if self.tod in self.network_config['distance_skim_tod']:
            return self.network_config['skim_matrix_designation_all_tods'] + self.network_config['skim_matrix_designation_limited']
        else:
            return self.network_config['skim_matrix_designation_all_tods']
        
    def _run_transit(self):
        return self.tod in self.network_config['transit_tod_list']
    
def create_tod_dict(network_config):
    tod_dict = {}
    for tod in network_config['tods']:
        tod_dict[tod] = TOD_Parameters(network_config, tod)
    return tod_dict

    