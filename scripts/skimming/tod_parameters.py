class TOD_Parameters(object):
    def __init__(self, network_settings, tod):
        self.network_settings = network_settings
        self.tod = tod
        self.skim_distance = self._skim_for_distance()
        self.skim_generalized_cost = self._skim_generalized_cost()
        self.skim_bike_walk = self._skim_for_bike_walk()
        self.skim_types = self._skim_types()
        self.run_transit = self._run_transit()
        self.skim_transit_fares = self._skim_transit_fares()

    def _skim_for_distance(self):
        return self.tod in self.network_settings.distance_skim_tod

    def _skim_generalized_cost(self):
        return self.tod in self.network_settings.generalized_cost_tod

    def _skim_for_bike_walk(self):
        return self.tod in self.network_settings.bike_walk_skim_tod

    def _skim_types(self):
        if self.tod in self.network_settings.distance_skim_tod:
            return (
                self.network_settings.skim_matrix_designation_all_tods
                + self.network_settings.skim_matrix_designation_limited
            )
        else:
            return self.network_settings.skim_matrix_designation_all_tods

    def _run_transit(self):
        return self.tod in self.network_settings.transit_tod_list

    def _skim_transit_fares(self):
        return self.tod in self.network_settings.fare_matrices_tod


def create_tod_dict(network_settings):
    tod_dict = {}
    for tod in network_settings.tods:
        tod_dict[tod] = TOD_Parameters(network_settings, tod)
    return tod_dict
