Soundcast is PSRC's activity-based travel model. This User's Guide provides an overview of the software and information of how to run the model and analyze its results. Use the navigation bar to the left to learn more. 

# Soundcast Overview

The Soundcast model package includes all estimated and calibrated demand models and scripts to assign demand onto road and transit networks. Soundcast's demand models were developed as part of the DaySim activity model framework by consultants [RSG](http://www.rsginc.com/). As shown in the figure below, the demand models process land use, demographics, and network inputs to produce trip tables by user class and time of day. These trips (i.e., 'demand') are then assigned to travel networks using [INRO's Emme software](http://www.inrosoftware.com/). If network assignment hasn't yet reached equilibrium, cost and time skims are sent back to the DaySim demand models to produce trip tables that incorporate network conditions from the latest model iteration. Upon convergence (specified as a configurable parameter) the model estimation will conclude and produce summary reports.

![Soundcast flow diagram](http://i61.tinypic.com/2u5xjwn.jpg)

# Hardware Recommendations
	- 100 GB disk space for each model run
	- 32 GB RAM recommended
	- Minimum of 12 processors

(Soundcast can be run on machines with less memory and fewer processors, but run time will be extended.)

# Software Recommendations
	- INRO Emme 4 License, with capability for processing 4000-zone matrices
	- Only tested on 64-bit Windows 7 OS
	- Anaconda Python Package (Python 2.7 with helper libraries included)

# External Resources

- [Activity-Based Modeling at PSRC](http://www.psrc.org/data/models/abmodel/)
- [Soundcast Technical Design Document]()
- [Soundcast GitHub Repo](https://github.com/psrc/soundcast)
- [Acitivty-Based Model Primer](http://onlinepubs.trb.org/onlinepubs/shrp2/SHRP2_C46.pdf)
- [PSRC Staff](http://www.psrc.org/about/contact/staff-roster/)