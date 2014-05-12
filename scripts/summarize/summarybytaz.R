


##################***********************set up*******************##########################
library(plyr)
library(data.table)
library(rhdf5)
library(ggplot2)
library(car)
library(daysimutil)
library(xtable)
library(reshape2)
library(knitr)


paths<- vector(mode = "list", length=2)
run_path<-getwd()
run_path = unlist(strsplit(run_path, split="Visualization", fixed=TRUE))[1]

# the run path needs to be changed
run_path <- "R:/Yingqian/RSummaryInputs" 

paths <-c(paste(run_path, "/daysim_outputs.h5",sep = ""),
          paste(run_path, "/survey_new.h5", sep = ""))
dist_sum <- paste(run_path, "/district_summary", sep = "")


# Give a descriptive name of the two datasets that are being compared
# For now we will assume the first dataset is ALWAYS the model, and the second is ALWAYS
# the survey
names(paths)<- c("Model", "Survey")
type <- names(paths)
district_file <- paste(run_path, "/Districts_County.csv",sep = "")
OutputDir <- "R:/ABModelDevelopment/Visualization/tables"



###Some convenience functions to make summaries more readable
# We  want to put this into the HDF5 file, but it's not there yet
recode <- function(dataset){
  dataset$mode[dataset$mode==1] <- "walk"
  dataset$mode[dataset$mode==2] <- "bike"
  dataset$mode[dataset$mode==3] <- "sov"
  dataset$mode[dataset$mode==4] <- "hov2"
  dataset$mode[dataset$mode==5] <- "hov3+"
  dataset$mode[dataset$mode==6] <- "transit"
  dataset$mode[dataset$mode==7] <- "other"
  dataset$mode[dataset$mode==8] <- "school_bus"
  dataset$mode[dataset$mode==9] <- "other"
  
  dataset$dpurp[dataset$dpurp==0] <- "home"
  dataset$dpurp[dataset$dpurp==1] <- "work"
  dataset$dpurp[dataset$dpurp==2] <- "school"
  dataset$dpurp[dataset$dpurp==3] <- "escort"
  dataset$dpurp[dataset$dpurp==4] <- "personal business"
  dataset$dpurp[dataset$dpurp==5] <- "shop"
  dataset$dpurp[dataset$dpurp==6] <- "meal"
  dataset$dpurp[dataset$dpurp==7] <- "social"
  dataset$dpurp[dataset$dpurp==8] <- "recreational"
  dataset$dpurp[dataset$dpurp==9] <- "medical"
  dataset$dpurp[dataset$dpurp==10] <- "other"
  dataset
}

recode_tours <- function(dataset){
  dataset$tmodetp[dataset$tmodetp==1] <- "walk"
  dataset$tmodetp[dataset$tmodetp==2] <- "bike"
  dataset$tmodetp[dataset$tmodetp==3] <- "sov"
  dataset$tmodetp[dataset$tmodetp==4] <- "hov2"
  dataset$tmodetp[dataset$tmodetp==5] <- "hov3+"
  dataset$tmodetp[dataset$tmodetp==6] <- "transit"
  dataset$tmodetp[dataset$tmodetp==7] <- "other"
  dataset$tmodetp[dataset$tmodetp==8] <- "school_bus"
  dataset$tmodetp[dataset$tmodetp==9] <- "other"
  
  dataset$pdpurp[dataset$pdpurp==0] <- "home"
  dataset$pdpurp[dataset$pdpurp==1] <- "work"
  dataset$pdpurp[dataset$pdpurp==2] <- "school"
  dataset$pdpurp[dataset$pdpurp==3] <- "escort"
  dataset$pdpurp[dataset$pdpurp==4] <- "personal business"
  dataset$pdpurp[dataset$pdpurp==5] <- "shop"
  dataset$pdpurp[dataset$pdpurp==6] <- "meal"
  dataset$pdpurp[dataset$pdpurp==7] <- "social"
  dataset$pdpurp[dataset$pdpurp==8] <- "recreational"
  dataset$pdpurp[dataset$pdpurp==9] <- "medical"
  dataset$pdpurp[dataset$pdpurp==10] <- "other"
  dataset
}

recode_districts<-function(dataset){
  # change the input file
  dataset$District[dataset$District==1] <- "Lakewood"
  dataset$District[dataset$District==2] <- "SE Pierce"
  dataset$District[dataset$District==3] <- "Tacoma"
  dataset$District[dataset$District==4] <- "Federal Way"
  dataset$District[dataset$District==5] <- "Kent"
  dataset$District[dataset$District==6] <- "Burien"
  dataset$District[dataset$District==7] <- "Issaquah"
  dataset$District[dataset$District==8] <- "Bellevue"
  dataset$District[dataset$District==9] <- "Redmond"
  dataset$District[dataset$District==10] <- "South Seattle"
  dataset$District[dataset$District==11] <- "Seattle CBD"
  dataset$District[dataset$District==12] <- "Capitol Hill"
  dataset$District[dataset$District==13] <- "North Seattle"
  dataset$District[dataset$District==14] <- "Shoreline"
  dataset$District[dataset$District==15] <- "Lynnwood"
  dataset$District[dataset$District==16] <- "Mill Creek"
  dataset$District[dataset$District==17] <- "Everett"
  dataset$District[dataset$District==18] <- "Marysville"
  dataset$District[dataset$District==19] <- "Kitsap"
  dataset$District[dataset$District==20] <- "External/PNR"
  dataset
}


get_total <- function(exp_fac)
{
  total <- sum(exp_fac)
  if(total<1)
  {
    total <- nrow(exp_fac)
  }
  total 
}

######################################################################################
# READ IN DATA

zone_district<- read.csv(district_file)
zone_district<-recode_districts(zone_district)

for(i in 1:length(paths))
{
  
  for(group in get_group_names(paths[i]))
  {
    table<- h5group_to_table(paths[i], group)
    table_name <- unlist(strsplit(group, split='/', fixed=TRUE))
    table_name <- paste(table_name[2],toString(i), sep="_")
    assign(table_name, table)
  }
}
#####################################################################
### RECODE DATA FOR READABILITY

Trip_1<-recode(Trip_1)
Trip_2 <-recode(Trip_2)

Tour_1<-recode_tours(Tour_1)
Tour_2<-recode_tours(Tour_2)


#alter the -1 expansion factor in the Household_2, Person_2
Household_2$hhexpfac[Household_2$hhexpfac < 0] <- 0
Person_2$psexpfac[Person_2$psexpfac < 0] <- 0
Trip_2$trexpfac[Trip_2$trexpfac < 0] <- 0
Tour_2$toexpfac[Tour_2$toexpfac < 0] <- 0
#end alter


#Households by district
hhs_zone_1 <- merge(zone_district, Household_1, by.y = "hhtaz", by.x = "TAZ")
hhs_district_1 <- aggregate(hhs_zone_1$hhexpfac, by = list(hhs_zone_1$District), length)
colnames(hhs_district_1) <- c("District", "NumHHs")
hhs_zone_2 <- merge(zone_district, Household_2, by.y = "hhtaz", by.x = "TAZ")
hhs_district_2 <- aggregate(hhs_zone_2$hhexpfac, by = list(hhs_zone_2$District), sum)
colnames(hhs_district_2) <- c("District", "NumHHs")

#Persons by district
PersonWithHHtaz_1 <- merge(Person_1, Household_1, by = "hhno")
Persons_zone_1 <- merge(zone_district, PersonWithHHtaz_1, by.y = "hhtaz", by.x = "TAZ")
Persons_district_1 <- aggregate(Persons_zone_1$ psexpfac, by = list(Persons_zone_1$ District), length)
colnames(Persons_district_1) <- c("District", "NumPSs")
PersonWithHHtaz_2 <- merge(Person_2, Household_2, by = "hhno")
Persons_zone_2 <- merge(zone_district, PersonWithHHtaz_2, by.y = "hhtaz", by.x = "TAZ")
Persons_district_2 <- aggregate(Persons_zone_2$ psexpfac, by = list(Persons_zone_2$ District), sum)
colnames(Persons_district_2) <- c("District", "NumPSs")

#Model: Households by taz
hhs_taz_1 <- aggregate(Household_1$ hhexpfac, by = list(Household_1$ hhtaz), length)
colnames(hhs_taz_1) <- c("TAZ", "NumHHs")


#Model: Persons by taz
Persons_taz_1 <- aggregate(PersonWithHHtaz_1$ psexpfac, by = list(PersonWithHHtaz_1$ hhtaz), length)
colnames(Persons_taz_1) <- c("TAZ", "NumPSs")


MinTaz <- 1
MaxTaz <- 3700

SetDefaultValue <- function(taz_level_data, default_field, default_value){
  data <- merge(taz_level_data, zone_district[MinTaz:MaxTaz, ], by = "TAZ", all = TRUE)
  data[default_field][is.na(data[default_field])] <- default_value
  return (data)
}


##################***********************main body*******************##########################

#VMT
PersonTrip_zone_1 <- merge(Persons_zone_1, Trip_1, by = c("hhno","pno"))
VehicleTrips_zone_1 <- subset(PersonTrip_zone_1, dorp == 1)

VehicleMiles_taz_1 <- aggregate(VehicleTrips_zone_1$ travdist, by = list(VehicleTrips_zone_1$ TAZ), sum)
colnames(VehicleMiles_taz_1) <- c("TAZ", "VehicleMiles")
VMTPerPerson_taz_1 <- merge(VehicleMiles_taz_1, Persons_taz_1, by = "TAZ" )
VMTPerPerson_taz_1["VMTPPS"] <- round(VMTPerPerson_taz_1$ VehicleMiles / VMTPerPerson_taz_1$ NumPSs, 2)
VMTPerPerson_taz_1["VehicleMiles"] <- NULL
VMTPerPerson_taz_1["NumPSs"] <- NULL
VMTPerPerson_taz_1 <- SetDefaultValue(VMTPerPerson_taz_1, "VMTPPS", -1)
VMTPerPerson_taz_1_file <- paste(OutputDir, "/VMTPerPerson_hhtaz.csv", sep = "")
write.csv(VMTPerPerson_taz_1, VMTPerPerson_taz_1_file)

Workers_taz_1 <- aggregate(PersonWithHHtaz_1$ psexpfac, by = list(PersonWithHHtaz_1$ pwtaz), length)
colnames(Workers_taz_1) <- c("TAZ", "NumPSs")
VehicleMiles_pwtaz_1 <- aggregate(VehicleTrips_zone_1$ travdist, by = list(VehicleTrips_zone_1$ pwtaz), sum)
colnames(VehicleMiles_pwtaz_1) <- c("TAZ", "VehicleMiles")
VMTPerPerson_pwtaz_1 <- merge(VehicleMiles_pwtaz_1, Workers_taz_1, by = "TAZ" )
VMTPerPerson_pwtaz_1["VMTPPS"] <- round(VMTPerPerson_pwtaz_1$ VehicleMiles / VMTPerPerson_pwtaz_1$ NumPSs, 2)
VMTPerPerson_pwtaz_1["VehicleMiles"] <- NULL
VMTPerPerson_pwtaz_1["NumPSs"] <- NULL
VMTPerPerson_pwtaz_1 <- SetDefaultValue(VMTPerPerson_pwtaz_1, "VMTPPS", -1)
VMTPerPerson_pwtaz_1_file <- paste(OutputDir, "/VMTPerPerson_pwtaz.csv", sep = "")
write.csv(VMTPerPerson_pwtaz_1, VMTPerPerson_pwtaz_1_file)


#mode share
modeShare <- function(modetp){
  SOV <- sum(modetp=="sov")
  HOV <- sum(modetp=="hov2"|modetp=="hov3+")
  transit <- sum(modetp =="transit")
  walk <- sum(modetp == "walk")
  bike <- sum(modetp == "bike")
  modeShare <- as.vector(c(SOV, HOV, transit, walk, bike)/length(modetp))
  return (modeShare)
}


home_Based_Tour_1 <- subset(Tour_1, parent == 0)
home_Based_Tour_hh_1 <- merge(home_Based_Tour_1, Household_1, by="hhno")
home_Based_Tour_modeShare_1 <- aggregate(home_Based_Tour_hh_1$ tmodetp, by = list(home_Based_Tour_hh_1$ hhtaz), FUN=modeShare)
home_Based_Tour_modeShare_1 <- as.data.frame(cbind(home_Based_Tour_modeShare_1$ Group.1, home_Based_Tour_modeShare_1$ x))
colnames(home_Based_Tour_modeShare_1) <- c("TAZ", "SOV", "HOV", "transit", "walk", "bike")

home_Based_Tour_modeShare_1 <- SetDefaultValue(home_Based_Tour_modeShare_1, c("SOV", "HOV", "transit", "walk", "bike"), -1)


home_Based_Tour_modeShare_1_file <- paste(OutputDir, "/home_Based_Tour_modeShare_taz.csv", sep = "")
write.csv(home_Based_Tour_modeShare_1, home_Based_Tour_modeShare_1_file)


#Average work/school commute distance by residence, employment/residence, school location
Workers <- PersonWithHHtaz_1$ pwtyp > 0
Students <- PersonWithHHtaz_1$ pstyp > 0

commute_dist_index <- PersonWithHHtaz_1[Workers]$ pwaudist > 0.05 & PersonWithHHtaz_1[Workers]$ pwaudist < 200
commute_dist_by_hhtaz_1 <- aggregate(PersonWithHHtaz_1[Workers]$ pwaudist[commute_dist_index], by = list(PersonWithHHtaz_1[Workers]$ hhtaz[commute_dist_index]), mean)
colnames(commute_dist_by_hhtaz_1) <- c("TAZ", "CDIST")
commute_dist_by_hhtaz_1 <- SetDefaultValue(commute_dist_by_hhtaz_1, "CDIST", -1)
commute_dist_by_hhtaz_1_file <- paste(OutputDir, "/work_commute_dist_by_hhtaz.csv", sep = "")
write.csv(commute_dist_by_hhtaz_1, commute_dist_by_hhtaz_1_file)

commute_dist_by_pwtaz_1 <- aggregate(PersonWithHHtaz_1[Workers]$ pwaudist[commute_dist_index], by = list(PersonWithHHtaz_1[Workers]$ pwtaz[commute_dist_index]), mean)
colnames(commute_dist_by_pwtaz_1) <- c("TAZ", "CDIST")
commute_dist_by_pwtaz_1 <- SetDefaultValue(commute_dist_by_pwtaz_1, "CDIST", -1)
commute_dist_by_pwtaz_1_file <- paste(OutputDir, "/work_commute_dist_by_pwtaz.csv", sep = "")
write.csv(commute_dist_by_pwtaz_1, commute_dist_by_pwtaz_1_file)


scommute_dist_index <- PersonWithHHtaz_1[Students]$ psaudist > 0.05 & PersonWithHHtaz_1[Students]$ psaudist < 200
scommute_dist_by_hhtaz_1 <- aggregate(PersonWithHHtaz_1[Students]$ psaudist[scommute_dist_index], by = list(PersonWithHHtaz_1[Students]$ hhtaz[scommute_dist_index]), mean)
colnames(scommute_dist_by_hhtaz_1) <- c("TAZ", "CDIST")
scommute_dist_by_hhtaz_1 <- SetDefaultValue(scommute_dist_by_hhtaz_1, "CDIST", -1)
scommute_dist_by_hhtaz_1_file <- paste(OutputDir, "/school_commute_dist_by_hhtaz.csv", sep = "")
write.csv(scommute_dist_by_hhtaz_1, scommute_dist_by_hhtaz_1_file)

scommute_dist_by_pstaz_1 <- aggregate(PersonWithHHtaz_1[Students]$ psaudist[scommute_dist_index], by = list(PersonWithHHtaz_1[Students]$ pstaz[scommute_dist_index]), mean)
colnames(scommute_dist_by_pstaz_1) <- c("TAZ", "CDIST")
scommute_dist_by_pstaz_1 <- SetDefaultValue(scommute_dist_by_pstaz_1, "CDIST", -1)
scommute_dist_by_pstaz_1_file <- paste(OutputDir, "/school_commute_dist_by_pstaz.csv", sep = "")
write.csv(scommute_dist_by_pstaz_1, scommute_dist_by_pstaz_1_file)

#Destination TAZ
Dtaz_1 <- aggregate(Trip_1$trexpfac, by = list(Trip_1$dtaz), length)
colnames(Dtaz_1) <- c("TAZ", "NumTrips")
Dtaz_1 <- subset(Dtaz_1, TAZ >= MinTaz & TAZ <= MaxTaz)
Dtaz_1_file <- paste(OutputDir, "/Dest_by_taz.csv", sep = "")
write.csv(Dtaz_1,Dtaz_1_file)

hhs_taz_1_file <- paste(OutputDir, "/hhs_by_taz.csv", sep = "")
write.csv(hhs_taz_1,hhs_taz_1_file)




#some demographic summary
if(TRUE){
  Persons_district <- merge(Persons_district_1, Persons_district_2, by = "District")
  Persons_district["Difference"] <- round(Persons_district$ NumPSs.x - Persons_district$ NumPSs.y, 0)
  Persons_district["Percent Difference"] <- round(100 * (Persons_district$ NumPSs.x - Persons_district$ NumPSs.y)/Persons_district$ NumPSs.y, 2)
  colnames(Persons_district) <- c("District", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
  
  Persons_district_file <- paste(OutputDir, "/TotalPersons_district.csv", sep = "")
  write.csv(Persons_district, Persons_district_file)
  
  
  #Has TransitPass: Model, taz
  HasTransitPass_taz_1 <- aggregate(PersonWithHHtaz_1$ ptpass, by = list(PersonWithHHtaz_1$ hhtaz), sum)
  colnames(HasTransitPass_taz_1) <- c("TAZ", "NumHasPass")
  TransitPassPercentage_taz_1 <- merge(HasTransitPass_taz_1, Persons_taz_1, by = "TAZ", all = TRUE)
  TransitPassPercentage_taz_1["Percent"] <- 100 * (TransitPassPercentage_taz_1$NumHasPass / TransitPassPercentage_taz_1$NumPSs)
  TransitPassPercentage_taz_1["NumHasPass"] <- NULL
  TransitPassPercentage_taz_1[ "NumPSs"] <- NULL
  TransitPassPercentage_taz_1 <- SetDefaultValue(TransitPassPercentage_taz_1, "Percent", -1)
  TransitPassPercentage_taz_1[ "District"] <- NULL
  
  TransitPassPercentage_taz_1_file <- paste(OutputDir, "/TransitPassPercentage_taz_1.csv", sep = "")
  write.csv(TransitPassPercentage_taz_1, TransitPassPercentage_taz_1_file)
  
  #Has TransitPass: district
  HasTransitPass_district_1 <- aggregate(Persons_zone_1$ ptpass, by = list(Persons_zone_1$District), sum)
  colnames(HasTransitPass_district_1) <- c("District", "NumHasPass")
  TransitPassPercentage_district_1 <- merge(HasTransitPass_district_1, Persons_district_1, by = "District")
  TransitPassPercentage_district_1["Percent"] <- 100 * (TransitPassPercentage_district_1$NumHasPass / TransitPassPercentage_district_1$NumPSs)
  TransitPassPercentage_district_1["NumHasPass"] <- NULL
  TransitPassPercentage_district_1[ "NumPSs"] <- NULL
  HasTransitPass_district_2 <- aggregate(Persons_zone_2$ psexpfac * Persons_zone_2$ ptpass, by = list(Persons_zone_2$District), sum)
  colnames(HasTransitPass_district_2) <- c("District", "NumHasPass")
  TransitPassPercentage_district_2 <- merge(HasTransitPass_district_2, Persons_district_2, by = "District")
  TransitPassPercentage_district_2["Percent"] <- 100* (TransitPassPercentage_district_2$NumHasPass / TransitPassPercentage_district_2$NumPSs)
  TransitPassPercentage_district_2["NumHasPass"] <- NULL
  TransitPassPercentage_district_2[ "NumPSs"] <- NULL
  
  TransitPassPercentage_district <- merge(TransitPassPercentage_district_1, TransitPassPercentage_district_2, by = "District")
  TransitPassPercentage_district["Difference"] <- TransitPassPercentage_district$ Percent.x - TransitPassPercentage_district$ Percent.y
  colnames(TransitPassPercentage_district) <- c("District", names(paths[1]), names(paths[2]), "Difference")
  TransitPassPercentage_district_file <- paste(OutputDir, "/TransitPassPercentage_district.csv", sep = "")
  write.csv(TransitPassPercentage_district, TransitPassPercentage_district_file)
  
  
  #Auto ownership: district
  AutoOwnership_district_1 <- aggregate(hhs_zone_1$ hhvehs, by = list(hhs_zone_1$ District), sum)
  colnames(AutoOwnership_district_1) <- c("District", "NumAutos")
  AutoOwnership_district_2 <- aggregate(hhs_zone_2$ hhexpfac * hhs_zone_2$ hhvehs, by = list(hhs_zone_2$ District), sum)
  colnames(AutoOwnership_district_2) <- c("District", "NumAutos")
  
  AutoOwnership_district <- merge(AutoOwnership_district_1, AutoOwnership_district_2, by = "District")
  AutoOwnership_district["Difference"] <- round(AutoOwnership_district$ NumAutos.x - AutoOwnership_district$ NumAutos.y, 0)
  AutoOwnership_district["Percent Difference"] <- round(100 * (AutoOwnership_district$ NumAutos.x - AutoOwnership_district$ NumAutos.y)/AutoOwnership_district$ NumAutos.y, 2)
  colnames(AutoOwnership_district) <- c("District", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
  
  AutoOwnership_district_file <- paste(OutputDir, "/AutoOwnership_district.csv", sep = "")
  write.csv(AutoOwnership_district, AutoOwnership_district_file)
  
  
  #Auto ownership per household: district
  AutoOwnershipPerhh_district_1 <- merge(AutoOwnership_district_1, hhs_district_1, by = "District")
  AutoOwnershipPerhh_district_1["AutoPerHH"] <- round(AutoOwnershipPerhh_district_1$ NumAutos / AutoOwnershipPerhh_district_1$ NumHHs, 2)
  AutoOwnershipPerhh_district_1["NumAutos"] <- NULL
  AutoOwnershipPerhh_district_1["NumHHs"] <- NULL
  
  AutoOwnershipPerhh_district_2 <- merge(AutoOwnership_district_2, hhs_district_2, by = "District")
  AutoOwnershipPerhh_district_2["AutoPerHH"] <- round(AutoOwnershipPerhh_district_2$ NumAutos / AutoOwnershipPerhh_district_2$ NumHHs, 2)
  AutoOwnershipPerhh_district_2["NumAutos"] <- NULL
  AutoOwnershipPerhh_district_2["NumHHs"] <- NULL
  
  AutoOwnershipPerhh_district <- merge(AutoOwnershipPerhh_district_1, AutoOwnershipPerhh_district_2, by = "District")
  AutoOwnershipPerhh_district["Difference"] <- round(AutoOwnershipPerhh_district$ AutoPerHH.x - AutoOwnershipPerhh_district$ AutoPerHH.y, 2)
  AutoOwnershipPerhh_district["Percent Difference"] <- round(100 * (AutoOwnershipPerhh_district$ AutoPerHH.x - AutoOwnershipPerhh_district$ AutoPerHH.y)/AutoOwnershipPerhh_district$ AutoPerHH.y, 2)
  colnames(AutoOwnershipPerhh_district) <- c("District", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
  
  AutoOwnershipPerhh_district_file <- paste(OutputDir, "/AutoOwnershipPerhh_district.csv", sep = "")
  write.csv(AutoOwnershipPerhh_district, AutoOwnershipPerhh_district_file)
  
  
}



if(TRUE){
VehicleMiles_district_1 <- aggregate(VehicleTrips_zone_1$ travdist, by = list(VehicleTrips_zone_1$ District), sum)
colnames(VehicleMiles_district_1) <- c("District", "VehicleMiles")

VMTPerPerson_district_1 <- merge(VehicleMiles_district_1, Persons_district_1, by = "District" )
VMTPerPerson_district_1["VMTPPS"] <- round(VMTPerPerson_district_1$ VehicleMiles / VMTPerPerson_district_1$ NumPSs, 2)
VMTPerPerson_district_1["VehicleMiles"] <- NULL
VMTPerPerson_district_1["NumPSs"] <- NULL


PersonTrip_zone_2 <- merge(Persons_zone_2, Trip_2, by = c("hhno","pno"))
VehicleTrips_zone_2 <- subset(PersonTrip_zone_2, dorp == 1)
VehicleMiles_district_2 <- aggregate(VehicleTrips_zone_2$ travdist * VehicleTrips_zone_2$ trexpfac, by = list(VehicleTrips_zone_2$ District), sum)
colnames(VehicleMiles_district_2) <- c("District", "VehicleMiles")

VMTPerPerson_district_2 <- merge(VehicleMiles_district_2, Persons_district_2, by = "District" )
VMTPerPerson_district_2["VMTPPS"] <- round(VMTPerPerson_district_2$ VehicleMiles / VMTPerPerson_district_2$ NumPSs, 2)
VMTPerPerson_district_2["VehicleMiles"] <- NULL
VMTPerPerson_district_2["NumPSs"] <- NULL

VMTPerPerson_district <- merge(VMTPerPerson_district_1, VMTPerPerson_district_2, by = "District")

VMTPerPerson_district["Difference"] <- round(VMTPerPerson_district$ VMTPPS.x - VMTPerPerson_district$ VMTPPS.y, 2)
VMTPerPerson_district["Percent Difference"] <- round(100 * (VMTPerPerson_district$ VMTPPS.x - VMTPerPerson_district$ VMTPPS.y)/VMTPerPerson_district$ VMTPPS.y, 2)
colnames(VMTPerPerson_district) <- c("District", names(paths[1]), names(paths[2]), "Difference", "PctDiff")

VMTPerPerson_district_file <- paste(OutputDir, "/VMTPerPerson_district.csv", sep = "")
write.csv(VMTPerPerson_district, VMTPerPerson_district_file)

#Destination TAZ
Dtaz_1 <- aggregate(Trip_1$trexpfac, by = list(Trip_1$dtaz), length)
colnames(Dtaz_1) <- c("TAZ", "NumTrips")
Dtaz_1 <- subset(Dtaz_1, TAZ >= MinTaz & TAZ <= MaxTaz)
Dtaz_2 <- aggregate(Trip_2$trexpfac, by = list(Trip_2$dtaz), sum)
colnames(Dtaz_2) <- c("TAZ", "NumTrips")
Dtaz_2 <- subset(Dtaz_2, TAZ >= MinTaz & TAZ <= MaxTaz)
Dtaz <- merge(Dtaz_1, Dtaz_2, by = "TAZ", all = TRUE)
#change NA into 0
Dtaz$ NumTrips.x[is.na(Dtaz$ NumTrips.x)] <- 0
Dtaz$ NumTrips.y[is.na(Dtaz$ NumTrips.y)] <- 0
#end change
Dtaz["Difference"] <- round(Dtaz$ NumTrips.x - Dtaz$ NumTrips.y, 0)
Dtaz["Percent Difference"] <- round(100 * (Dtaz$ NumTrips.x - Dtaz$ NumTrips.y)/Dtaz$ NumTrips.y, 2)
colnames(Dtaz) <- c("TAZ", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
#how to show the non meaningful percent difference value
Dtaz$ PctDiff[Dtaz$ PctDiff == Inf] <- 0

###step2: output the destination taz data
#Dtaz_1_file <- paste(OutputDir, "/Dtaz1.csv", sep = "")
#write.csv(Dtaz_1,Dtaz_1_file)
#Dtaz_2_file <- paste(OutputDir, "/Dtaz2.csv", sep = "")
#write.csv(Dtaz_2,Dtaz_2_file)
Dtaz_file <- paste(OutputDir, "/DestTaz.csv", sep = "")
write.csv(Dtaz,Dtaz_file)



#################Job number at taz level
JobIndex_1 <- (Person_1$pwtyp > 0)
Jobs_1 <- Person_1$ pwtaz[JobIndex_1]
Jobstaz_1 <- aggregate(Jobs_1, by = list(Jobs_1), length)
colnames(Jobstaz_1) <- c("TAZ", "NumJobs")

JobIndex_2 <- (Person_2$pwtyp > 0)
Jobs_2 <- Person_2$ pwtaz[JobIndex_2]
Jobstaz_2 <- aggregate(Jobs_2, by = list(Jobs_2), sum)
colnames(Jobstaz_2) <- c("TAZ", "NumJobs")

Jobstaz <- merge(Jobstaz_1, Jobstaz_2, by = "TAZ", all = TRUE)
#change NA into 0
Jobstaz$ NumJobs.x[is.na(Jobstaz$ NumJobs.x)] <- 0
Jobstaz$ NumJobs.y[is.na(Jobstaz$ NumJobs.y)] <- 0
#end change
Jobstaz["Difference"] <- round(Jobstaz$ NumJobs.x - Jobstaz$ NumJobs.y, 0)
Jobstaz["Percent Difference"] <- round(100 * (Jobstaz$ NumJobs.x - Jobstaz$ NumJobs.y)/Jobstaz$ NumJobs.y, 2)
colnames(Jobstaz) <- c("TAZ", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
#how to show the non meaningful percent difference value
Jobstaz$ PctDiff[Jobstaz$ PctDiff == Inf] <- 0
##step2
Jobstaz_file <- paste(OutputDir, "/JobsTaz.csv", sep = "")
write.csv(Jobstaz,Jobstaz_file)


################Trip destination district: show the destination district in model(1) and survey(2)
###step1
TripMerge_1 <- merge(zone_district, Trip_1, by.y = "dtaz", by.x = "TAZ")
DDist_1 <- aggregate(TripMerge_1$trexpfac, by = list(TripMerge_1$District), length)
colnames(DDist_1) <- c("District", "NumTrips")
DDist_1 <- subset(DDist_1, District != "External/PNR")
TripMerge_2 <- merge(zone_district, Trip_2, by.y = "dtaz", by.x = "TAZ")
DDist_2 <- aggregate(TripMerge_2$trexpfac, by = list(TripMerge_2$District), sum)
colnames(DDist_2) <- c("District", "NumTrips")
DDist_2 <- subset(DDist_2, District != "External/PNR")
DDist <- merge(DDist_1, DDist_2, by = "District")
DDist["Difference"] <- round(DDist$ NumTrips.x - DDist$ NumTrips.y, 0)
DDist["Percent Difference"] <- round(100 * (DDist$ NumTrips.x - DDist$ NumTrips.y)/DDist$ NumTrips.y, 2)
colnames(DDist) <- c("District", names(paths[1]), names(paths[2]), "Difference", "PctDiff")
###step2
DDist_file <- paste(OutputDir, "/DestDistrict.csv", sep = "")
write.csv(DDist,DDist_file)
}
