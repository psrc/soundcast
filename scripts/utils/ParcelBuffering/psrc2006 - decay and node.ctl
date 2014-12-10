RUNLAB psrc 2006 decay and node buffering
PRNTFN psrc_2006_decay.prn                         print file name

OUTDIR C:\Temp\DaySim\ParcelBuffering\Output\   output directory pathname
OUTFNM psrc_parcel_decay&node_2006.dat             output parcel buffer file name (file type always ascii)
OUTDLM 1                                             outfile file delimiter (1=space, 2=tab, 3=comma) 

INPDIR C:\Temp\DaySim\ParcelBuffering\buffering_inputs\    input directory pathname
PARCFT 1                                             input parcel file type (1=dbf, 2=ascii - space or tab delimited)
PARCFN parcels.dbf                     input parcel base data file name
INTSFT 1                                             input intersection file type (0=none, 1=dbf, 2=ascii - space or tab delimited)
INTSFN psrc_intersections_2006.dbf                  input intersection data file name
TRSTFT 1                                             input transit stop file type (0=none, 1=dbf, 2=ascii - space or tab delimited)
TRSTFN psrc_transitstops_2006.dbf                   input transit stop data file name
OPSPFT 1                                             input open space file type (0=none, 1=dbf, 2=ascii - space or tab delimited)
OPSPFN psrc_openspace_2006.dbf                      input open space data file name
NODEFT 2                                             input open space file type (0=none, 1=dbf, 2=ascii - space or tab delimited)
NODEFN psrc_node_xys.dat                              input node xy data file
CIRCFT 3                                             input circuity file type (0=none, 1=dbf, 2=ascii - space or tab delimited, 3=node-node)
CIRCFN psrc_node_node_shortest_path.txt             input circuity data file name

DLIMIT 15840.0           orthogonal distance limit (feet) above which parcels are not considered for buffering

BTYPE1 2                 type for buffer 1 (1 = flat, 2 = logistic decay, 3 = exponential decay)
BDIST1  660.0            buffer 1 inflection distance (feet) - used in different way depending on buffer type    
BOFFS1 2640.0            buffer1 offset distance (feet) (used for logistic decay type)
DECAY1 0.76               buffer 1 decay slope parameter (used for logistic decay type)

BTYPE2 2                 type for buffer 2 (1 = flat, 2 = logistic decay, 3 = exponential decay)
BDIST2 1320.0            buffer 2 inflecton distance (feet) - used in different way depending on buffer type    
BOFFS2 2640.0            buffer2 offset distance (feet) (used for logistic decay type)
DECAY2 0.76               buffer 2 decay slope parameter (used for logistic decay type)
