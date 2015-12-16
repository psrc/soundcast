library(data.table)
library(rhdf5)
library(sqldf)
library(plyr)


# This script converts the .dat files of the household survey data into HDF5.

h5_path <- "J:/Projects/Surveys/HHTravel/Survey2014/Data/DaySim/survey14.h5"
survey_path <-"J:/Projects/Surveys/HHTravel/Survey2014/Data/DaySim"

survey_hh_file = "hrecP2.dat"
survey_per_file = "precP2.dat"
survey_pday_file = "pdayP2.dat"
survey_hday_file = "hdayP2.dat"
survey_tour_file = "tourP2.dat"
survey_trip_file = "tripP2.dat"

# survey_trip_gps_file <- "trip_gps.txt"

h5_persons <- "/Person"
h5_households <- "/Household"
h5_tours <- "/Tour"
h5_trips <- "/Trip"
h5_persondays <- "/PersonDay"
h5_householddays <- "/HouseholdDay"


table_to_h5group <- function(h5_path, h5_data_root, dataset) {
  # Convenience function for taking a dataframe-like object and
  # writing it to an hdf5 group. Each column is converted to a 1D
  # dataset. Assumes numeric data. Assumes datasets don't already
  # exist.
  try(h5createGroup(h5_path, h5_data_root))
  for(column in names(dataset))
  {
    if(column == "deptm")
    {
      deptm_array <- subset(dataset, select=column)
      deptm_array <- floor(deptm_array/100)*60 +  deptm_array %% 100
      
      h5write(deptm_array,
              h5_path,
              paste(h5_data_root, column, sep="/"))
    }
    else
    {
      h5write(subset(dataset, select=column),
              h5_path,
              paste(h5_data_root, column, sep="/"))
    }
  }
}

try(h5createFile(h5_path), silent=TRUE)

survey_hh <- read.table(paste(survey_path,"/",survey_hh_file,sep=""),header=T,sep="")
survey_persons<- read.table(paste(survey_path,"/",survey_per_file,sep=""),header=T,sep="")
survey_pdays <- read.table(paste(survey_path,"/",survey_pday_file,sep=""),header=T,sep="")
survey_hdays <- read.table(paste(survey_path,"/",survey_hday_file,sep=""),header=T,sep="")
survey_tours <- read.table(paste(survey_path,"/",survey_tour_file,sep=""),header=T,sep="")
survey_trips <- read.table(paste(survey_path,"/",survey_trip_file,sep=""),header=T,sep="")

# survey_trips_gps <- read.table(paste(survey_path,"/",survey_trip_gps_file,sep=""),header=T,sep="\t")

# survey_trips_update <- merge(survey_trips, survey_trips_gps, c("hhno", "pno", "day", "deptm"), all.x = TRUE)


# survey_trips_new_weights <-sqldf(c("UPDATE survey_trips_update SET trexpfac =expfacgpsdiv2 WHERE expfacgpsdiv2>0", "SELECT * from main.survey_trips_update"), method="raw")
# drops <- c("recid", "tripnum", "mmode", "expfac2", "expfac2div2", "expfacgps", "expfacgpsdiv2", "gpsfact2", "gpsfactx", "X", "X_1", "X_2", "arrtm_y")
# survey_trips_final <- survey_trips_new_weights[,!(names(survey_trips_new_weights) %in% drops)]
# names(survey_trips_final)[names(survey_trips_final) =='arrtm_x'] <- 'arrtm'

table_to_h5group(h5_path, h5_households, survey_hh) 
table_to_h5group(h5_path, h5_persons, survey_persons) 
table_to_h5group(h5_path, h5_persondays, survey_pdays) 
table_to_h5group(h5_path, h5_householddays, survey_hdays) 
table_to_h5group(h5_path, h5_tours, survey_tours) 
table_to_h5group(h5_path, h5_trips, survey_trips_final) 




