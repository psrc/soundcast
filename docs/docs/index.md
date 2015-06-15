# Soundcast

PSRC's Activity-Based Travel Model

## Overview

Soundcast is a collection of statistical models used by the Puget Sound Regional Council to forecast regional travel around the Puget Sound area of Washington state. The model includes several different components to estimate details of travel choices over time. This User's Guide focuses on practical steps to implement Soundcast, but more technical details are available from [PSRC's website](http://www.psrc.org/assets/11924/SoundCastDesign2014.pdf)

## Model Structure

The Soundcast model package includes all estimated and calibrated demand models and scripts to assign demand onto road and transit networks. Soundcast's demand models were developed as part of the DaySim activity model framework by consultants [RSG](http://www.rsginc.com/). As shown in the figure below, the demand models process land use, demographics, and network inputs to produce trip tables by user class and time of day. These trips (i.e., 'demand') are then assigned to travel networks using INRO's Emme software. If network assignment hasn't yet reached equilibrium, cost and time skims are sent back to the DaySim demand models to produce trip tables that incorporate network conditions from the latest model iteration. Upon convergence (specified as a configurable parameter) the model estimation will conclude and produce summary reports. 

![Alt text](http://i61.tinypic.com/2u5xjwn.jpg)

## Soundcast Setup

Scripts

## 
This code is intended to control the exchange of data between the PSRC's network model in Inro's Emme 4.0 
software to our new Activity Based Model (ABM) system that is being developed in the DaySim software. 

DaySim requires several measures of accessibility from our network model in the form of matrices of 
travel times, costs, and distances. This Python code is intended to:

	+ Import estimates of personal travel by vehicle class and time of day from DaySim
	+ Estimate Truck Trips by time of day for:
		- Light Trucks
		- Medium Trucks
		- Heavy Trucks
	+ Estimate any special generators of travel not captured in DaySim for items like
		- External Stations
		- Sport's Stadiums
		- Airports
		- Convention Centers
	+ Run Higway, Transit and Non-Motorized Assignments for various vehicle classes and times of day
	+ Generate matrices of travel information related to Time, Cost and Distance for all od-pairs in our 4000 zone travel model system.

The vehicle skims include 756 matrices (12 time periods x 63 skims). Previous data exchanges between our 
model systems relied upon transfer via comma-separated formats.  We have implemented code that utilizes 
an HDF5 database as a storage container for all Emme model output.  The intent is to use hdf5 during 
runtime for all model processes as there are a variety of api's in various languages to access the data. 
For now we are assuming an HDF5 database for each time period but this might change as we move forward 
with implementation.

##Emme Data Structure
To effectively utilize multiple cores on a pc for model runs, we need to have a separate Emme databank 
and corresponding Emme project for every time period that we wish to run in parallel.  So in order to run 
12 highway assignments concurrently, we need to have 12 distinct project files with only one databank in 
each.

The current folder structure is:

Root Directory (for example, C:\ABM)
 -> Banks
    -> Bank1
    -> Bank2
    -> Bank3
    -> Bank4
    etc.
 -> Projects
    -> Project1
    -> Project2
    -> Project3
    -> Project4
    etc.

During code testing, we are relying on hardcoding all paths to the project files in the code.  Once 
testing of the code is complete, we plan to implement a refined approach to selecting the projects either 
through the use of a control file or possibly a tkinter based dialog selection using tkFileDialog.

##Input Files##
As of now, there are a variety of input files that exist in various ascii formats.  These files currently 
reside in the "Inputs" folder under each bank.  The inputs inlcude:

	1. user_classes.txt (dictionary)
		This file contains relevant data about the vehicle classes used in the skimming process. 

It is used to create all relevant matrices, link attributes and assignment 
and skim parameters used in the course of the run.
	2. vdfs.txt (input)
		This file contains the specification of the volume delay functions need for assignments in Emme
	3. tolls.txt (input)
		This file contains the specification of the link level tolls for the network
	4. link_calculation.txt (Emme Tool Specification)
		This file contains the specification for the link calculator tool from Emme Modeller
	5. node_calculation.txt (Emme Tool Specification)
		This file contains the specification for the node calculator tool from Emme Modeller
	6. general_attribute_based_skim.txt (Emme Tool Specification)
		This file contains the specification for Path Based Skimming of a network attribute from Emme Modeller
	7. general_generalized_cost_skim.txt (Emme Tool Specification)
		This file contains the specification for Path Based Skimming of an od object from Emme Modeller
	8. general_path_based_assignment.txt (Emme Tool Specification)
		This file contains the specification for Path Based Assignments from Emme Modeller
	9. general_path_based_volume.txt (Emme Tool Specification)
		This file contains the specification for Path Based Class Specific volumes from Emme Modeller

We are working on a solution to generalize the creation of as many of these inputs as possible.  The vdfs 
and tolls file could reside in our hdf5 datastore.  The Emme specifications might be auto-generated based 
on the inputs in the user_class dictionary.  For now, these specification files work for networks with 21 
user classes.

##Time Periods
DaySim calculates travel for all hours of the day.  In order to provide meaningful accessibility data to 
DaySim and still maintain reasonable model run times, the PSRC network model will be various time periods 
per day for various modal purposes.  The difference by mode reflects the availability of network related 
data by mode and time of day.  

###Time Periods for Highway Assignments
The time periods for Highway Assignments are are defined as:
 
	1. Early AM		5:00 am - 6:00 am
	2. AM Peak Hour 1	6:00 am - 7:00 am
	3. AM Peak Hour 2	7:00 am - 8:00 am
	4. AM Peak Hour 3	8:00 am - 9:00 am
	5. AM Peak Hour 4	9:00 am - 10:00 am
	6. Midday		10:00 am - 2:00 pm
	7. PM Peak Hour 1	2:00 pm - 3:00 pm
	8. PM Peak Hour 2	3:00 pm - 4:00 pm
	9. PM Peak Hour 3	4:00 pm - 5:00 pm
	10. PM Peak Hour 4	5:00 pm - 6:00 pm
	11. Evening		6:00 pm – 8:00 pm
	12. Overnight		8:00 pm - 5:00 am

###Time Periods for Transit Assignments
The time periods for Transit Assignments are are defined as:
 
	1. AM			6:00 am - 9:00 am
	2. Midday		9:00 am - 3:00 pm
	3. PM			3:00 pm - 6:00 pm
	4. Evening		6:00 pm - 8:00 pm
	5. Night		8:00 pm - 6:00 am

###Vehicle Classification for Highway Assignments
Assignment Specifications are currently set to work for a 21 class assignments as needed by DaySim.  The 

21 classes are:

	1. SOV Toll Income Level 1
	2. SOV Toll Income Level 2
	3. SOV Toll Income Level 3
	4. SOV No Toll Income Level 1
	5. SOV No Toll Income Level 2
	6. SOV No Toll Income Level 3
	7. HOV 2 Toll Income Level 1
	8. HOV 2 Toll Income Level 2
	9. HOV 2 Toll Income Level 3
	10. HOV 2 No Toll Income Level 1
	11. HOV 2 No Toll Income Level 2
	12. HOV 2 No Toll Income Level 3
	13. HOV 3 Toll Income Level 1
	14. HOV 3 Toll Income Level 2
	15. HOV 3 Toll Income Level 3
	16. HOV 3 No Toll Income Level 1
	17. HOV 3 No Toll Income Level 2
	18. HOV 3 No Toll Income Level 3
	19. Light Trucks
	20. Medium Trucks
	21. Heavy Trucks

###Value of Time
The value of time categories used the assignment are coming from DaySim and are:

	Class		$ per Hour		
			Cat #1	Cat #2	Cat #3
	SOV		$2.00	$8.00	$20.00
	HOV 2		$4.00	$16.00	$40.00
	HOV 3+		$6.00	$24.00	$60.00
	Trucks		$40.00	$45.00	$50.00		

	Class		minutes per cent		
			Cat #1	Cat #2	Cat #3
	SOV		0.3000	0.0750	0.0300
	HOV 2		0.1500	0.0375	0.0150
	HOV 3+		0.1000	0.0250	0.0100
	Trucks		0.0150	0.0133	0.0120


###Matrix Definition
The code uses the Emme Tool for creating matrices to create the 84 total demand and skim matrices needed 
for the model run.  The code overwrites any existing matrices as DaySim will be feeding new demand each 
time it access Emme for skimming and the skims should change due to the new demand.  There are 21 demand 
trip tables and 63 total skim tables being created for auto modes (time, cost and distance).  
Naming convention is: class (2 characters), toll/notoll(2 characters), income (1 number), type (1 
character)

	1. svtl1v - SOV Toll Income Level 1 Demand
	2. svtl2v - SOV Toll Income Level 1 Demand
	3. svtl3v - SOV Toll Income Level 1 Demand
	4. svnt1v - SOV No Toll Income Level 1 Demand
	5. svnt2v - SOV No Toll Income Level 1 Demand
	6. svnt3v - SOV No Toll Income Level 1 Demand
	7. h2tl1v - HOV 2 Toll Income Level 1 Demand
	8. h2tl2v - HOV 2 Toll Income Level 1 Demand
	9. h2tl3v - HOV 2 Toll Income Level 1 Demand
	10. h2nt1v - HOV 2 No Toll Income Level 1 Demand
	11. h2nt2v - HOV 2 No Toll Income Level 1 Demand
	12. h2nt3v - HOV 2 No Toll Income Level 1 Demand
	13. h3tl1v - HOV 3+ Toll Income Level 1 Demand
	14. h3tl2v - HOV 3+ Toll Income Level 1 Demand
	15. h3tl3v - HOV 3+ Toll Income Level 1 Demand
	16. h3nt1v - HOV 3+ No Toll Income Level 1 Demand
	17. h3nt2v - HOV 3+ No Toll Income Level 1 Demand
	18. h3nt3v - HOV 3+ No Toll Income 
	19. lttrkv - Light Truck Demand
	20. mdtrkv - Medium Truck Demand
	21. hvtrkv - Heavy Truck Demand
	22. svtl1t - SOV Toll Income Level 1 Time
	23. svtl2t - SOV Toll Income Level 1 Time
	24. svtl3t - SOV Toll Income Level 1 Time
	25. svnt1t - SOV No Toll Income Level 1 Time
	26. svnt2t - SOV No Toll Income Level 1 Time
	27. svnt3t - SOV No Toll Income Level 1 Time
	28. h2tl1t - HOV 2 Toll Income Level 1 Time
	29. h2tl2t - HOV 2 Toll Income Level 1 Time
	30. h2tl3t - HOV 2 Toll Income Level 1 Time
	31. h2nt1t - HOV 2 No Toll Income Level 1 Time
	32. h2nt2t - HOV 2 No Toll Income Level 1 Time
	33. h2nt3t - HOV 2 No Toll Income Level 1 Time
	34. h3tl1t - HOV 3+ Toll Income Level 1 Time
	35. h3tl2t - HOV 3+ Toll Income Level 1 Time
	36. h3tl3t - HOV 3+ Toll Income Level 1 Time
	37. h3nt1t - HOV 3+ No Toll Income Level 1 Time
	38. h3nt2t - HOV 3+ No Toll Income Level 1 Time
	39. h3nt3t - HOV 3+ No Toll Income 
	40. lttrkt - Light Truck Time
	41. mdtrkt - Medium Truck Time
	42. hvtrkt - Heavy Truck Time
	43. svtl1c - SOV Toll Income Level 1 Cost
	44. svtl2c - SOV Toll Income Level 1 Cost
	45. svtl3c - SOV Toll Income Level 1 Cost
	46. svnt1c - SOV No Toll Income Level 1 Cost
	47. svnt2c - SOV No Toll Income Level 1 Cost
	48. svnt3c - SOV No Toll Income Level 1 Cost
	49. h2cl1c - HOV 2 Toll Income Level 1 Cost
	50. h2cl2c - HOV 2 Toll Income Level 1 Cost
	51. h2cl3c - HOV 2 Toll Income Level 1 Cost
	52. h2nt1c - HOV 2 No Toll Income Level 1 Cost
	53. h2nt2c - HOV 2 No Toll Income Level 1 Cost
	54. h2nt3c - HOV 2 No Toll Income Level 1 Cost
	55. h3cl1c - HOV 3+ Toll Income Level 1 Cost
	56. h3cl2c - HOV 3+ Toll Income Level 1 Cost
	57. h3cl3c - HOV 3+ Toll Income Level 1 Cost
	58. h3nt1c - HOV 3+ No Toll Income Level 1 Cost
	59. h3nt2c - HOV 3+ No Toll Income Level 1 Cost
	60. h3nt3c - HOV 3+ No Toll Income 
	61. lttrkc - Light Truck Cost
	62. mdtrkc - Medium Truck Cost
	63. hvtrkc - Heavy Truck Cost
	64. svtl1d - SOV Toll Income Level 1 Distance
	65. svtl2d - SOV Toll Income Level 1 Distance
	66. svtl3d - SOV Toll Income Level 1 Distance
	67. svnt1d - SOV No Toll Income Level 1 Distance
	68. svnt2d - SOV No Toll Income Level 1 Distance
	69. svnt3d - SOV No Toll Income Level 1 Distance
	70. h2dl1d - HOV 2 Toll Income Level 1 Distance
	71. h2dl2d - HOV 2 Toll Income Level 1 Distance
	72. h2dl3d - HOV 2 Toll Income Level 1 Distance
	73. h2nt1d - HOV 2 No Toll Income Level 1 Distance
	74. h2nt2d - HOV 2 No Toll Income Level 1 Distance
	75. h2nt3d - HOV 2 No Toll Income Level 1 Distance
	76. h3dl1d - HOV 3+ Toll Income Level 1 Distance
	77. h3dl2d - HOV 3+ Toll Income Level 1 Distance
	78. h3dl3d - HOV 3+ Toll Income Level 1 Distance
	79. h3nt1d - HOV 3+ No Toll Income Level 1 Distance
	80. h3nt2d - HOV 3+ No Toll Income Level 1 Distance
	81. h3nt3d - HOV 3+ No Toll Income 
	82. lttrkd - Light Truck Distance
	83. mdtrkd - Medium Truck Distance
	84. hvtrkd - Heavy Truck Distance

###Vehicle Matrix Calculations
The code creates three sets of skims for use by DaySim - travel time, generalized cost and distance.  All 
three skim procedures utilize the standard path based assignment analysis toolkits from Emme Modeller.  
The travel time skims are created by skimming auto time (timau) across all paths, distance skims are 
based on link length and the generalized cost skims use the conversion of toll costs to time via values 
of time as noted above.