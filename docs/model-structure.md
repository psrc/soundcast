*What are all the parts of Soundcast and how do they work together?*

# Model Structure
Soundcast is designed to run its processes in a specific order. Understanding this flow is critical to performing partial runs (e.g., traffic assignment or demand only) that will save processing time. Being able to recover from a crash mid-way through a model run requires knowledge of how the model's scripts are designed. The basic process is as follows.

## run_soundcast.py
Soundcast's primary controller script is run_soundcast.py. Most of the major model functions are controlled here, along with input_configuration.py, which controls which processes are run, and certain input values. The run_soundcast script is rather readable, with many processes self-documented by relevant function or variable names. As with all Python scripts in Soundcast, the main function of the scripts are contained in the main() function. This is the part of the script that is first executed. In run_soundcast, subprocesses are called in a specific order. Subprocesses are controlled by binary variables that are defined in input_configuration. If these control variables are defined as True in input_configuration, Soundcast will execute that subprocess. For instance, if the variable "run_copy_daysim_code" is defined as True in the configuration, then Soundcast will run the function to move all Daysim inputs into the local directory. Many times, if a model run is being run for another iteration, or has been stopped during a crash, these processes will not need to be repeated, so they are frequently turned off (set to False). The order of subprocesses exectued by run_soundcast are as follows:

	- parcel buffering (land use preparation for demand estimation)
	- parcel buffering summary (a CSV for error checking)
	- copy Daysim code
	- setup emmebank and project folders (for each time of day used in assignment)
	- copy large inputs to local directory
	- update household income to base year (2010) values
	- import networks
	- run all skims and paths (using seed trips for 0th iteration)
	- demand modeling with Daysim
	- assign truck and supplemental (external, special generator) trips
	- run skims and paths using Daysim demand results
	- repeat global demand and assignment for fixed number of iterations 

The number of global iterations is defined in input_configuration.py, as the length of the pop_sample array. Each value in this list represents an iteration of demand+skimming/assignment. The number corresponds to the population size being sampled on that run. Samples are used to reduce run time, and the sample size should gradually increase with each iteration. The number is actually the denominator of the population size. For instance pop_sample = [10,5,2] indicates that 3 global iterations will be performed. The first will use a population sample size of 1/10th the actual population, the next a sample of 1/5, and finally a sample of 1/2. 

# Inputs
Soundcast inputs will be provided as a zipped folder to users. However, at this time, inputs will only be available to users with authorized access to use Washington State's highly employment disaggregate data. PSRC is still working through solutions to provide model access to all users without access to this sensitive data. 

For users that are able to receive the input, the folder should be unzipped and stored on a local drive. The path must be specified in "input_configuration.py" and folder structure should not be changed. Soundcast copies all inputs into the local Soundcast directory to keep paths consistent, and allows for a central storage point of different model inputs. Input folders will typically be named to represent the land use and network year, e.g., 2010 or 2040. 

The inputs directory is structured as follows:

	- 4k	# inputs for truck model, based on estimates from trip-based 4k model
		- auto.h5
		- transit.h5
	- etc
		- daysim_outputs_seed_trips.h5    # seed trips to use on first iteration of DaySim
		- survey.h5    # 2006 household travel survey for DaySim estimation validation summaries
	- landuse
		- buffered_parcels.dat
		- daily_parking_costs.csv
		- hh_and_persons.h5
		- hourly_parking_costs.csv
		- parcels_military.csv    # Military employment data
		- parcels_urbansim.txt    # Primary land-use data at the parcel level
		- schema.ini
		- tazdata.in
	- networks
		- am_roadway.in
		- am_transit.in
		- am_turns.in
		... (roadway, transit, and turns network files for 5 times of day: am, md, pm, ev, ni)
		- vehicles.txt    # list of transit vehicles and characteristics
		- modes.txt    # list of modes and their characteristics
		- fixes
			- ferries
				- am_roadway.in
				... (roadway ferry flags for 5 times of day: am, md, pm, ev, ni)
		- rdly
			- am_rdly.txt
			... (rdly.txt for 5 times of day: am, md, pm, ev, ni)
		- various shapefiles for showing smooth network shapes, rather than blocky network topology. Edges 0-4 correspond to 5 times of day, in order: am, md, pm, ev, ni
	- supplemental
		- generation
		- distribution
		- trips
	- tolls
		- am_roadway_tolls.in
		- bridge_ferry_flags.in
		- ev_roadway_tolls.in
		- ferry_vehicle_fares.in
		- md_roadway_tolls.in
		- ni_roadway_tolls.in
		- pm_roadway_tolls.in
	- trucks
		- agshar.in
		- const.in
		- districts19_ga.ens
		- equipshar.in
		- heavy_trucks_reeb_ee.in
		- heavy_trucks_reeb_ei.in
		- heavy_trucks_reeb_ie.in
		- input_skims.txt
		- matrix_balancing_spec.txt
		- matric_calc_spec.txt
		- minshar.in
		- prodshar.in
		- special_gen_heavy_trucks.in
		- special_gen_light_trucks.in
		- special_gen_medium_trucks.in
		- tazdata.in
		- tcushar.in
		- truck_gen_calc_dict.txt
		- truck_matrices_dict.txt
		- truck_operating_costs.in
		- whlsshar.in
		
# Scripts
The scripts directory holds the many scripts that may be used in a SoundCast run. The directory structure and contents are described below.

## summarize
These scripts are used to produce primary model summaries. 

## benefit_cost
This directory holds a script and configuration for running the benefit-cost tool.

## calibration
The summaries for calibration operate off of daysim_outputs.h5 as compared to the survey in the survey.h5 file.

The main script that runs these summaries is called SCSummary.py. SCSummary writes out excel spreadsheets into the outputs directory.

## exploratory
This directory contains an ipython notebook that allows you to analyze model results interactively in SoundCastNotebook.ipynb. The notebook reads in daysim outputs and merges tables so you can easiy work with the data.

There is also a bike_summary.py in this directory. The file will be moved into a different directory once the bike model is completed.

## inputs
This folder contains inputs necessary to run the summary scripts.
### benefit_cost

*injury_rates.csv*
	
contains the property damanage, injury and fatal rates that occur per one vehicle miles traveled by PSRC's Facility Types. 
	
See [EMME codes](emme-codes) for Facility Types
	
*pollutant_rates.csv*
	
contains the amount of each pollutant per one million vehicle miles traveled for vehicle class and by speed.
##### calibration
This folder contains files used when running the calibration summary scipts.

*SurveyWorkFlow.csv*

includes the district to district trip flows from the household survey. This is used to determine whether the model is selecting the correct destinations in the destination choice model by comparing these flows to the model flow.

*TAZ_TAD_County.csv*
is a lookup table between each TAZ and which transportation analysis district(TAD) and which county the TAZ is in. This look-up allows for aggregations across TAZs to the district or to the county.

## mapping
Files in this directory allow for the automatic mapping of model results.

## notebooks
This directory contains a set of Python notebooks to do various summaries. It is currently a work-in-progress.

### standard
The standard directory contains the scripts for network summaries and other miscellany.

**daily_bank.py**

aggregates the individual time period results from each time period bank into one daily bank.

**net_summary_simplify.py**

takes the results of network_summary and formats them into tables in excel.

**network_summary.py**

summarizes the network results from EMME into an unformatted file with lists of links.

**parcel_summary.py**

summarizes statistics from the parcels file for error checking.

**RegionalCenterSummaries.py**

summarizes information about regional centers.
**
standard_summary_configuration.py**

contains configuration parameters for the standard summaries.