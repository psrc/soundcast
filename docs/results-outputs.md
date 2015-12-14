# Results and Outputs
As the model runs, results are stored in the 'outputs' directory of the local soundcast folder. Emme-related outputs are stored in 'projects' and 'banks' folders. Users can view results by time of day by opening up the corresponding project and bank in Emme. These files contain all time and cost skims by vehicle class and time of day. They are also available in a compressed format (hdf5) and, somewhat confusingly, created in the 'inputs' folder after an assignment iteration. They're stored in inputs because they're used as inputs to DaySim demand modeling, though they will represent the last assignment and skimming pass. These output files are named by their time period (e.g., 5to6.h5) and can be viewed interactively with Python or the [OMX Viewer](https://sites.google.com/site/openmodeldata/file-cabinet/omx-viewer) GUI.

Results of DaySim demand are stored in hdf5 format as well, in the 'daysim_outputs.h5' file stored in the 'outputs' folder. These outputs include details for all persons, households, trips, and tours taken in the region, for a typical travel day. These include all the details about demographics and trip characteristics like mode, purpose, time, origin and destination, and many others. 

Soundcast includes Python scripts to summarize model results and create output spreadsheets. The primary summaries are available in the following sheets:

	- network_summary.xlsx
	- Topsheet.xlsx

Other summaries are included for detailed DaySim and network summaries as needed. Users may also create their own summaries by directly evaluating the h5 output files.

**[File Information and Directory Structure](file-structure.md)**

**[Daysim Variable Definitions and Codes](https://github.com/psrc/soundcast/blob/master/Daysim1.8%20Users%20Guide.xlsx)**

# EMME Codes

Speed speedau
capacity Ul1

Facility Type:

	1 – Freeway
	2 – Expressway
	3 – Principal Arterial
	4 – Minor Arterial
	5 – Collector
	6 – Ramp
	8 – Centroid Connector


## *Matrix Names* ##

1. svtl1v SOV Toll Income Level 1 Demand
1. svtl2v SOV Toll Income Level 1 Demand
1. svtl3v SOV Toll Income Level 1 Demand
1. svnt1v SOV No Toll Income Level 1 Demand
1. svnt2v SOV No Toll Income Level 1 Demand
1. svnt3v SOV No Toll Income Level 1 Demand
1. h2tl1v HOV 2 Toll Income Level 1 Demand
1. h2tl2v HOV 2 Toll Income Level 1 Demand
1. h2tl3v HOV 2 Toll Income Level 1 Demand
1. h2nt1v HOV 2 No Toll Income Level 1 Demand
1. h2nt2v HOV 2 No Toll Income Level 1 Demand
1. h2nt3v HOV 2 No Toll Income Level 1 Demand
1. h3tl1v HOV 3+ Toll Income Level 1 Demand
1. h3tl2v HOV 3+ Toll Income Level 1 Demand
1. h3tl3v HOV 3+ Toll Income Level 1 Demand
1. h3nt1v HOV 3+ No Toll Income Level 1 Demand
1. h3nt2v HOV 3+ No Toll Income Level 1 Demand
1. h3nt3v HOV 3+ No Toll Income
1. lttrkv Light Truck Demand
1. mdtrkv Medium Truck Demand
1. hvtrkv Heavy Truck Demand
1. svtl1t SOV Toll Income Level 1 Time
1. svtl2t SOV Toll Income Level 1 Time
1. svtl3t SOV Toll Income Level 1 Time
1. svnt1t SOV No Toll Income Level 1 Time
1. svnt2t SOV No Toll Income Level 1 Time
1. svnt3t SOV No Toll Income Level 1 Time
1. h2tl1t HOV 2 Toll Income Level 1 Time
1. h2tl2t HOV 2 Toll Income Level 1 Time
1. h2tl3t HOV 2 Toll Income Level 1 Time
1. h2nt1t HOV 2 No Toll Income Level 1 Time
1. h2nt2t HOV 2 No Toll Income Level 1 Time
1. h2nt3t HOV 2 No Toll Income Level 1 Time
1. h3tl1t HOV 3+ Toll Income Level 1 Time
1. h3tl2t HOV 3+ Toll Income Level 1 Time
1. h3tl3t HOV 3+ Toll Income Level 1 Time
1. h3nt1t HOV 3+ No Toll Income Level 1 Time
1. h3nt2t HOV 3+ No Toll Income Level 1 Time
1. h3nt3t HOV 3+ No Toll Income
1. lttrkt Light Truck Time
1. mdtrkt Medium Truck Time
1. hvtrkt Heavy Truck Time
1. svtl1c SOV Toll Income Level 1 Cost
1. svtl2c SOV Toll Income Level 1 Cost
1. svtl3c SOV Toll Income Level 1 Cost
1. svnt1c SOV No Toll Income Level 1 Cost
1. svnt2c SOV No Toll Income Level 1 Cost
1. svnt3c SOV No Toll Income Level 1 Cost
1. h2cl1c HOV 2 Toll Income Level 1 Cost
1. h2cl2c HOV 2 Toll Income Level 1 Cost
1. h2cl3c HOV 2 Toll Income Level 1 Cost
1. h2nt1c HOV 2 No Toll Income Level 1 Cost
1. h2nt2c HOV 2 No Toll Income Level 1 Cost
1. h2nt3c HOV 2 No Toll Income Level 1 Cost
1. h3cl1c HOV 3+ Toll Income Level 1 Cost
1. h3cl2c HOV 3+ Toll Income Level 1 Cost
1. h3cl3c HOV 3+ Toll Income Level 1 Cost
1. h3nt1c HOV 3+ No Toll Income Level 1 Cost
1. h3nt2c HOV 3+ No Toll Income Level 1 Cost
1. h3nt3c HOV 3+ No Toll Income
1. lttrkc Light Truck Cost
1. mdtrkc Medium Truck Cost
1. hvtrkc Heavy Truck Cost
1. svtl1d SOV Toll Income Level 1 Distance
1. svtl2d SOV Toll Income Level 1 Distance
1. svtl3d SOV Toll Income Level 1 Distance
1. svnt1d SOV No Toll Income Level 1 Distance
1. svnt2d SOV No Toll Income Level 1 Distance
1. svnt3d SOV No Toll Income Level 1 Distance
1. h2dl1d HOV 2 Toll Income Level 1 Distance
1. h2dl2d HOV 2 Toll Income Level 1 Distance
1. h2dl3d HOV 2 Toll Income Level 1 Distance
1. h2nt1d HOV 2 No Toll Income Level 1 Distance
1. h2nt2d HOV 2 No Toll Income Level 1 Distance
1. h2nt3d HOV 2 No Toll Income Level 1 Distance
1. h3dl1d HOV 3+ Toll Income Level 1 Distance
1. h3dl2d HOV 3+ Toll Income Level 1 Distance
1. h3dl3d HOV 3+ Toll Income Level 1 Distance
1. h3nt1d HOV 3+ No Toll Income Level 1 Distance
1. h3nt2d HOV 3+ No Toll Income Level 1 Distance
1. h3nt3d HOV 3+ No Toll Income
1. lttrkd Light Truck Distance
1. mdtrkd Medium Truck Distance
1. hvtrkd Heavy Truck Distance


**Mode Codes**

                a   Auto
                s   NoTollSOV
                e   TollSOV
                h   NoTollHOV2
                d   TollHOV2
                i   NoTollHOV3
                m   TollHOV3
                j   NoTollVans
                g   TollVans
                v   LgtTruck
                u   MedTruck
                t   HvyTruck
                b   LocalBus
                p   ExpBus
                n   BRT
                r   LRT
                c   CRT
                o   StrCar
                f   Ferry
                w   Walk
                x   WalkAcc
                k   BikeTr
                l   BikeLn
                q   BikeShldr