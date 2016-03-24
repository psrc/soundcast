from scripts.skimming.SkimsAndPaths import *
from scripts.EmmeProject import *

def revive(project_name):
    '''Populate emme trip tables and skims with h5 data'''
    
    my_project = EmmeProject(project_name)

    # Create empty matrices
    define_matrices(my_project)
    
    # Load trip tables
    hdf5_trips_to_Emme(my_project, hdf5_file_path)
    
    # Populate intrazonals
    populate_intrazonals(my_project)
    
    # Load skims from hdf5
    # For a single TOD
    skim_h5 = h5py.File(r'D:/archive/soundcast/inputs/' + my_project.tod + '.h5', "r+")

    zonesDim = len(my_project.current_scenario.zone_numbers)
    zones = my_project.current_scenario.zone_numbers

    #Create a dictionary lookup where key is the taz id and value is it's numpy index.
    dictZoneLookup = dict((value,index) for index,value in enumerate(zones))

    #create an index of trips for this TOD. This prevents iterating over the entire array (all trips).
    tod_index = create_trip_tod_indices(my_project.tod)

    matrix_dict = text_to_dictionary('demand_matrix_dictionary')
    uniqueMatrices = set(matrix_dict.values())

    for matrix in my_project.bank.matrices():
        # Add the matrix if its available from the skims h5 database
        if matrix.name in skim_h5['Skims'].keys():

            print 'processing matrix: ' + str(matrix.name)

            emme_matrix = ematrix.MatrixData(indices=[zones,zones],type='f')
            matrix_id = my_project.bank.matrix(str(matrix.name)).id

            emme_matrix.from_numpy(skim_h5['Skims'][matrix.name][:])
            my_project.bank.matrix(matrix.id).set_data(emme_matrix, my_project.current_scenario)

            print 'added matrix: ' + str(matrix.name)
        else:
            continue

def start_pool(project_list):
    pool = Pool(processes=parallel_instances)
    pool.map(revive,project_list[0:parallel_instances])
    
    pool.close()

def main():

    for i in range (0, 12, parallel_instances):
        l = project_list[i:i+parallel_instances]
        start_pool(l)

if __name__ == '__main__':
	main()