# Soundcast Users' Guide

The Soundcast model package includes all estimated and calibrated demand models and scripts to assign demand onto road and transit networks. Soundcast's demand models were developed as part of the DaySim activity model framework by consultants [RSG](http://www.rsginc.com/). As shown in the figure below, the demand models process land use, demographics, and network inputs to produce trip tables by user class and time of day. These trips (i.e., 'demand') are then assigned to travel networks using [INRO's Emme software](http://www.inrosoftware.com/). If network assignment hasn't yet reached equilibrium, cost and time skims are sent back to the DaySim demand models to produce trip tables that incorporate network conditions from the latest model iteration. Upon convergence (specified as a configurable parameter) the model estimation will conclude and produce summary reports. 

![Soundcast flow diagram](http://i61.tinypic.com/2u5xjwn.jpg)

## Hardware Recommendations
	- 100 GB disk space for each model run
	- 32 GB RAM recommended
	- Minimum of 12 processors

(Soundcast can be run on machines with less memory and fewer processors, but run time will be extended.)

## Software Recommendations
	- INRO Emme 4 License, with capability for processing 4000-zone matrices
	- Only tested on 64-bit Windows 7 OS
	- Anaconda Python Package (Python 2.7 with helper libraries included)

## Initial Setup

All Soundcast scripts are stored within a public [GitHub repository](https://github.com/psrc/soundcast). If you're familiar with Git technology, you can [clone](http://git-scm.com/docs/git-clone) the repository on your modeling machine. 

Alternatively, you can download all the code as a ZIP file. 

![Download GitHub ZIP](http://oi60.tinypic.com/dxmo2u.jpg)

### Python Packages and Paths
It's recommended to [install the Anaconda 2.7 Python package](http://continuum.io/downloads) to run Soundcast. This package should include all necessary libraries to run the model. When installing, make sure the installer adds the Anaconda install to the system path (or add it yourself after installing). It's important that this install is the one referenced whenever the "python" program is invoked from a command. Many machines might include another Python install; it's okay to leave other versions installed, but you'll want to update the path variable to point only to the Anaconda version. 

After installing Anaconda, you must change Emme's settings to use the Anaconda installation by default. Otherwise, scripts that interact with Emme will use another install without the necessary libraries. To change the Python version used by Emme, select Tools (from the main taskbar) and click 'Application Options'. Under the Modeller tab is a field "Python path", which by default probably looks like:

	%<$EmmePath>%/Python27

![Emme Python version settings](http://oi57.tinypic.com/2466ecp.jpg)

Replace this path with the full path to the Anaconda Python executable (python.exe). Depending on where Anaconda was installed, it may be something like:

	C:\Anaconda

## Run Configuration
Once Python paths and versions are defined and installed, inputs must be provided and configuration settings specified. Input locations and run settings are controlled centrally from the file **"input_configuration.py".** This is a Python script, but it simply holds variable definitions which are passed into other scripts when the model runs. The input configuration contains paths to input directories, scenario names and analysis years, and also controls number of iterations and convergence criteria. Additionally, it allows finer control over specific model components. For instance, all demand, skimming, and assignment iterations can be turned off, and only specific summarization scripts run, or the model can be set to stop after importing certain input files. 

Scenarios and input paths are defined as follows by default. Users must point to the location of these inputs and ensure the inputs follow a format as defined later in this guide. 

	- base_year = '2010'  # This should always be 2010 unless the base year changes
	- scenario_name = '2040'
	- daysim_code = 'R:/soundcast/daysim' 
	- master_project = 'LoadTripTables'
	- base_inputs = 'R:/soundcast/inputs/' + scenario_name
	- network_buffer_inputs = 'R:/soundcast/inputs/parcel_buffering_network/parcel_buff_network_inputs.7z'
	- network_buffer_code = 'R:/SoundCast/util/parcel_buffering/'

The following variables act as control parameters for the model. They are mostly self-explanatory by their variable name. 

	- run_update_parking = False
	- run_convert_hhinc_2000_2010 = False
	- run_parcel_buffering = True
	- run_copy_daysim_code = True
	- run_setup_emme_project_folders = True
	- run_setup_emme_bank_folders = True
	- run_copy_large_inputs = True
	- run_import_networks = True
	- run_skims_and_paths_seed_trips = True
	- should_build_shadow_price =True
	- run_skims_and_paths = True
	- run_truck_model = True
	- run_supplemental_trips = True
	- run_daysim = True
	- run_parcel_buffer_summary = True
	- run_network_summary = True
	- run_soundcast_summary = True
	- run_travel_time_summary = True
	- run_create_daily_bank = True

For a basic run, these variables can be left in their default state as stored in the GitHub repository. This applies for all other variables in the input_configuration file, aside from the input directories listed above, which must be defined appropriately by the user.

Other important parameters that the user may which to adjust are the number of defined model iterations and population sample settings.

	- pop_sample = [10, 5, 1, 1, 1, 1]   
	- shadow_work = [1, 1, 1, 1]
	- shadow_con = 10 #%RMSE for shadow pricing to consider being converged
	- STOP_THRESHOLD = 0.025
	- parallel_instances = 12   # Number of simultaneous parallel processes. Must be a factor of 12.
	- max_iter = 50             # Assignment Convergence Criteria
	- best_relative_gap = 0.01  # Assignment Convergence Criteria
	- relative_gap = .0001
	- normalized_gap = 0.01

The population sample (pop_sample) is a list of population sample proportions for each iteration to be produced by the DaySim demand models. In the example above, the 10 implies 1/10th of the population will be modeled (to save time for the first pass), and 5 implies 1/5th, whereas 1 represents a full population run. The length of the list represents the number of times the model might be run, if it doesn't first converge.

The "shadow_work" variable represents the number of iterations for which shadow pricing will be run. This is an important part of the demand models, but consumes significant run time; the parameter should only be changed with good reason. 

The remaining variables in input_configuration are not intended to be changed by the user. Many are definitions that should not change, except with major model revisions. They're stored in this file for consistency, rather than scattering variable definitions across a number of scripts.

## Inputs
Soundcast inputs will be provided as a zipped folder to users. However, at this time, inputs will only be available to users with authorized access to use Washington State's highly employment disaggregate data. PSRC is still working through solutions to provide model access to all users without access to this sensitive data. 

For users that are able to receive the input, the folder should be unzipped and stored on a local drive. The path must be specified in "input_configuration.py" and folder structure should not be changed. Soundcast copies all inputs into the local Soundcast directory to keep paths consistent, and allows for a central storage point of different model inputs. Input folders will typically be named to represent the land use and network year, e.g., 2010 or 2040. 

The inputs directory should be structured as follows:

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

## Running the Model
Once the inputs have been properly structured and configuration defined, Soundcast can be started with a single command-line prompt. Open a command prompt and navigate to the location the soundcast directory. In the main directory, type:

	- python run_soundcast.py

This will call the run_soundcast script in Python, which is the master script file to start the model. Depending on the modules specified to run in input_configuration, Soundcast will be spawn its different processes. For a new run, this includes copying inputs into the local Soundcast directory, creating new directories to store outputs, initializing Emme projects, and finally starting an iteration of DaySim demand models and assignment. The model should run until convergence, or until maximum numbers of global iterations are attained, and (if specified) produce summary files and end. 

## Log Files
The Soundcast run can be monitored in the command prompt, since many functions include print statements, but since it takes many hours to complete a run, all important status outputs are stored in log files in the main Soundcast directory. The two primary log files are:

	- soundcast_log.txt
	- skims_log.txt

The soundcast log contains high-level informatino about when different modules of the run began and were completed. Here's an example from the first 2 iterations of a soundcast log:

	06/02/2015 11:25:39 AM ------------------------NEW RUN STARTING---------------------------------------
	06/02/2015 11:26:11 AM  build_seed_skims starting
	06/02/2015 07:39:14 PM build_seed_skims took 8:13:03.651000
	06/02/2015 07:39:15 PM We're on iteration 0


	06/02/2015 07:39:15 PM starting run 2015-06-02 19:39:15.084000
	06/02/2015 07:39:15 PM  modify_config starting
	06/02/2015 07:39:15 PM modify_config took 0:00:00
	06/02/2015 07:39:15 PM  daysim_assignment starting
	06/02/2015 07:39:15 PM Start of 0 iteration of Daysim
	06/02/2015 08:28:47 PM End of 0 iteration of Daysim
	06/02/2015 08:47:46 PM Start of 0 iteration of Skims and Paths
	06/03/2015 09:03:20 AM End of 0 iteration of Skims and Paths
	06/03/2015 09:03:20 AM daysim_assignment took 13:24:05.685000
	06/03/2015 09:03:20 AM  check_convergence starting
	06/03/2015 09:03:20 AM check_convergence took 0:00:00
	06/03/2015 09:03:20 AM We're on iteration 1


	06/03/2015 09:03:20 AM starting run 2015-06-03 09:03:20.784000
	06/03/2015 09:03:20 AM  modify_config starting
	06/03/2015 09:03:20 AM modify_config took 0:00:00
	06/03/2015 09:03:20 AM  daysim_assignment starting
	06/03/2015 09:03:20 AM Start of 1 iteration of Daysim
	06/03/2015 10:33:40 AM End of 1 iteration of Daysim
	06/03/2015 10:40:47 AM Start of 1 iteration of Skims and Paths
	06/03/2015 02:09:30 PM End of 1 iteration of Skims and Paths
	06/03/2015 02:09:30 PM daysim_assignment took 5:06:09.604000
	06/03/2015 02:09:30 PM  check_convergence starting
	06/03/2015 02:09:30 PM check_convergence took 0:00:00.015000
	06/03/2015 02:09:30 PM We're on iteration 2

The skims log provides details on when each assignment and skimming script began, how long it took to complete, and the resulting relative gap, for each user class and time of day.

## Results and Outputs
As the model runs, results are stored in the 'outputs' directory of the local soundcast folder. Emme-related outputs are stored in 'projects' and 'banks' folders. Users can view results by time of day by opening up the corresponding project and bank in Emme. These files contain all time and cost skims by vehicle class and time of day. They are also available in a compressed format (hdf5) and, somewhat confusingly, created in the 'inputs' folder after an assignment iteration. They're stored in inputs because they're used as inputs to DaySim demand modeling, though they will represent the last assignment and skimming pass. These output files are named by their time period (e.g., 5to6.h5) and can be viewed interactively with Python or the [OMX Viewer](https://sites.google.com/site/openmodeldata/file-cabinet/omx-viewer) GUI.

Results of DaySim demand are stored in hdf5 format as well, in the 'daysim_outputs.h5' file stored in the 'outputs' folder. These outputs include details for all persons, households, trips, and tours taken in the region, for a typical travel day. These include all the details about demographics and trip characteristics like mode, purpose, time, origin and destination, and many others. 

Soundcast includes Python scripts to summarize model results and create output spreadsheets. The primary summaries are available in the following sheets:

	- network_summary.xlsx
	- Topsheet.xlsx

Other summaries are included for detailed DaySim and network summaries as needed. Users may also create their own summaries by directly evaluating the h5 output files. 

## Resources

- [Activity-Based Modeling at PSRC](http://www.psrc.org/data/models/abmodel/)
- [Soundcast Technical Design Document](http://www.psrc.org/assets/11924/SoundCastDesign2014.pdf)
- [Soundcast GitHub Repo](https://github.com/psrc/soundcast)
- [Acitivty-Based Model Primer](http://onlinepubs.trb.org/onlinepubs/shrp2/SHRP2_C46.pdf)
- [PSRC Staff](http://www.psrc.org/about/contact/staff-roster/)