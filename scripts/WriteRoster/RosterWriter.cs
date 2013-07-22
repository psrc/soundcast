using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;


namespace DaysimTool {
	class RosterWriter {
		public static void Main() {

			StreamWriter writeRoster = new StreamWriter("C:/temp/psrc_2.1/psrc_roster_test_write.csv");
			writeRoster.WriteLine("#variable,mode,path-type,vot-group,start-minute,end-minute,length,file-type, name, field, transpose, blend-variable,blend-path-type,factor,scaling");

			// the field "name" now needs to include the name of the hdf5 file 
			// plus the skim; but the tod.name doesn't need to be specified inside the file


			List<TimeOfDay> highway_times_of_day = HighwayDimensions.DefineTimeOfDay();
			List<Mode> highway_modes = HighwayDimensions.DefineModes();
			List<PathType> highway_path_types = HighwayDimensions.DefinePathTypes();
			List<SkimVariable> highway_skim_variables = HighwayDimensions.DefineSkimVariables();
			List<ValueOfTime> sov_toll_highway_values_of_time = HighwayDimensions.DefineTollSOVValuesofTime();
			List<ValueOfTime> hov_toll_highway_values_of_time = HighwayDimensions.DefineTollHOVValuesofTime();
			List<ValueOfTime> no_toll_highway_values_of_time = HighwayDimensions.DefineNoTollValuesofTime();

			List<Mode> transit_modes = TransitDimensions.DefineModes();
			List<TimeOfDay> transit_times_of_day = TransitDimensions.DefineTimesOfDay();
			List<PathType> transit_path_types = TransitDimensions.DefinePathTypes();
			List<SkimVariable> transit_skim_variables = TransitDimensions.DefineSkimVariables();
			List<ValueOfTime> transit_values_of_time = TransitDimensions.DefineValuesofTime();

			List<Mode> nonmotorized_modes = NonMotorizedDimensions.DefineModes();
			List<TimeOfDay> nonmotorized_times_of_day = NonMotorizedDimensions.DefineTimesOfDay();
			List<PathType> nonmotorized_path_types = NonMotorizedDimensions.DefinePathTypes();
			List<SkimVariable> nonmotorized_skim_variables = NonMotorizedDimensions.DefineSkimVariables();
			List<ValueOfTime> nonmotorized_values_of_time = NonMotorizedDimensions.DefineValuesofTime();

			//Write Highway Toll - SOV
			foreach (TimeOfDay tod in highway_times_of_day) {
				foreach (ValueOfTime vot in sov_toll_highway_values_of_time) {
					foreach (Mode mode in highway_modes) {
						//foreach (PathType pt in highway_path_types) {
							foreach (SkimVariable skim in highway_skim_variables) {

								var pt =highway_path_types[1];
								string skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
								string specificskim = "Skims/"+mode.emme_code + pt.emme_code + vot.vot_id.ToString() + skim.variable_emme_code;
								string fullpathtoskim = skimpath + specificskim;


								RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
								// we only need one distance skim for all day- let 5 to 6 stand in
								if ((skim.variable_name_in_file == "Distance") && (tod.time_name != "5to6")) {

								}
								else if ((skim.variable_name_in_file == "Distance") && (tod.time_name == "5to6")) {
									record.start_minute = 0;
									record.end_minute = 1439;

									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
								else {
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
							}
						}
					//}
				}
			}

			//Write Highway Toll - HOV
			foreach (TimeOfDay tod in highway_times_of_day) {
				foreach (ValueOfTime vot in hov_toll_highway_values_of_time) {
					foreach (Mode mode in highway_modes) {
						//foreach (PathType pt in highway_path_types) {
							foreach (SkimVariable skim in highway_skim_variables) {

								var pt =highway_path_types[1];
								string skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
								string specificskim = "Skims/"+mode.emme_code + pt.emme_code + vot.vot_id.ToString() + skim.variable_emme_code;
								string fullpathtoskim = skimpath + specificskim;


								RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
								// we only need one distance skim for all day- let 5 to 6 stand in
								if ((skim.variable_name_in_file == "Distance") && (tod.time_name != "5to6")) {

								}
								else if ((skim.variable_name_in_file == "Distance") && (tod.time_name == "5to6")) {
									record.start_minute = 0;
									record.end_minute = 1439;

									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
								else {
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
							}
						}
					//}
				}
			}

			//Write Highway No Toll
			foreach (TimeOfDay tod in highway_times_of_day) {
				foreach (ValueOfTime vot in no_toll_highway_values_of_time) {
					foreach (Mode mode in highway_modes) {
						//foreach (PathType pt in highway_path_types) {
							foreach (SkimVariable skim in highway_skim_variables) {

								var pt =highway_path_types[0];
								string skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
								string specificskim = "Skims/"+mode.emme_code + pt.emme_code + vot.vot_id.ToString() + skim.variable_emme_code;
								string fullpathtoskim = skimpath + specificskim;

								RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
								// we only need one distance skim for all day- let 5 to 6 stand in
								if ((skim.variable_name_in_file == "Distance") && (tod.time_name != "5to6")) {

								}
								else if ((skim.variable_name_in_file == "Distance") && (tod.time_name == "5to6")) {
									record.start_minute = 0;
									record.end_minute = 1439;

									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
								else {
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}
							}
						}
					//}
				}
			}

			writeRoster.Flush();

			//Write Transit
			foreach (TimeOfDay tod in transit_times_of_day) {
				foreach (ValueOfTime vot in transit_values_of_time) {
					foreach (Mode mode in transit_modes) {
						foreach (PathType pt in transit_path_types) {
							foreach (SkimVariable skim in transit_skim_variables) {

								string skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
								string specificskim = "Skims/"+mode.emme_code + skim.variable_emme_code;
								string fullpathtoskim = skimpath + specificskim;

								RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);

								// pick up fare for all times from the 9to10 file for now
								if (record.start_minute == 300 && skim.variable_name_roster == "fare") {
									record.start_minute = 0;
									record.end_minute = 1439;

									tod.time_name = "9to10";

									skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
									specificskim ="Skims/"+ mode.emme_code + skim.variable_emme_code;
									record.name = skimpath + specificskim;

									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
									+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
									record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
									record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
								}

								else if (skim.variable_name_roster != "fare") {
									// the overnight skims should have nulls for now
									if (record.start_minute == 1320) {
										writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + "null,null,1,FALSE,null,null,null,TRUE");
									}
									// PM as transpose of AM
									else if (record.start_minute == 960 && skim.variable_name_roster != "fare") {
										writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + "TRUE" + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
									}
									else {
										writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
										+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
										record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
										record.blend_var + ',' + record.blend_path_type + ',' + record.factor.ToString() + ',' + record.scaling);
									}
								}
							}
						}
					}
				}
			}

			writeRoster.Flush();

			//Write Nonmotorized
			foreach (TimeOfDay tod in nonmotorized_times_of_day) {
				foreach (ValueOfTime vot in nonmotorized_values_of_time) {
					foreach (Mode mode in nonmotorized_modes) {
						foreach (PathType pt in nonmotorized_path_types) {
							foreach (SkimVariable skim in nonmotorized_skim_variables) {

								string skimpath = string.Format(@"{0}.{1}/", tod.time_name, "h5");
								string specificskim = "Skims/"+"walkt";
								string fullpathtoskim = skimpath + specificskim;

								//Console.WriteLine(fullpathtoskim);
								//Console.ReadLine();
								if (skim.variable_name_roster == "distance") {
									//distance skim needs to be divided by 60, multiplied by mph, which 3 mph so 3/60 is the factor
									RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
									+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
									record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
									record.blend_var + ',' + record.blend_path_type + ',' + "0.05" + ',' + record.scaling);
								}
								else if (mode.mode_name == "walk") {
									RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
									+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
									record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
									record.blend_var + ',' + record.blend_path_type + ',' + record.factor + ',' + record.scaling);
								}
								else
								//bike time is the else
								{
									//assuming 15 mph speed on bike
									RosterRecord record = new RosterRecord(skim.variable_name_roster, mode.mode_name, pt.path_type_name, vot.vot_name, tod.start_time, tod.end_time, fullpathtoskim, skim.blend_variable, mode.factor);
									writeRoster.WriteLine(record.variable + ',' + record.mode + ',' + record.path_type + ','
									+ record.value_of_time_group + ',' + record.start_minute.ToString() + ',' + record.end_minute.ToString() + ',' +
									record.length + ',' + record.file_type + ',' + record.name + ',' + record.field + ',' + record.transpose + ',' +
									record.blend_var + ',' + record.blend_path_type + ',' + "0.20" + ',' + record.scaling);
								}

							}
						}
					}
				}
			}


			writeRoster.Flush();
			Console.WriteLine("All done.");
			Console.ReadLine();

		}

		public static class TransitDimensions {

			//for transit, I'm going to use the beginning of the time period to stand in 
			// for the entire longer period, i.e. 6 to 7 represents 6 to 9
			public static List<TimeOfDay> DefineTimesOfDay() {
				List<TimeOfDay> transit_times_of_day = new List<TimeOfDay>();
				//AM
				transit_times_of_day.Add(new TimeOfDay("7to8", 300, 539));
				//MD
				//for now have MD point to AM because we are not finished with the MD network yet
				transit_times_of_day.Add(new TimeOfDay("7to8", 540, 959));
				//PM
				transit_times_of_day.Add(new TimeOfDay("7to8", 960, 1079));
				//night
				//for now have night point to am because of an issue with the skims
				transit_times_of_day.Add(new TimeOfDay("7to8", 1079, 1319));
				transit_times_of_day.Add(new TimeOfDay("10to14", 1320, 299));

				return transit_times_of_day;
			}

			public static List<Mode> DefineModes() {
				List<Mode> transit_mode = new List<Mode>();
				transit_mode.Add(new Mode("transit", "transit"));
				return transit_mode;
			}

			public static List<PathType> DefinePathTypes() {
				List<PathType> transit_path_type = new List<PathType>();
				transit_path_type.Add(new PathType("local-bus", "transit", ""));
				return transit_path_type;
			}

			public static List<ValueOfTime> DefineValuesofTime() {
				List<ValueOfTime> transit_value_of_time = new List<ValueOfTime>();
				transit_value_of_time.Add(new ValueOfTime("all", -1, -1));
				return transit_value_of_time;
			}

			public static List<SkimVariable> DefineSkimVariables() {
				List<SkimVariable> transit_skim_variable = new List<SkimVariable>();
				transit_skim_variable.Add(new SkimVariable("ivtime", "ivtwa", "ivtwa", "null"));
				transit_skim_variable.Add(new SkimVariable("iwaittime", "iwtwa", "iwtwa", "null"));
				transit_skim_variable.Add(new SkimVariable("xwaittime", "twtwa", "twtwa", "null"));
				transit_skim_variable.Add(new SkimVariable("fare", "mfmfarbx", "mfmfarbx", "null"));
				transit_skim_variable.Add(new SkimVariable("nboard", "ndbwa", "ndbwa", "null"));
				transit_skim_variable.Add(new SkimVariable("ivtprembus", "ivtwap", "ivtwap", "null"));
				transit_skim_variable.Add(new SkimVariable("ivtlitrail", "ivtwar", "ivtwar", "null"));
				transit_skim_variable.Add(new SkimVariable("ivtcomrail", "ivtwac", "ivtwac", "null"));
				transit_skim_variable.Add(new SkimVariable("ivtpxferry", "ivtwaf", "ivtwaf", "null"));
				return transit_skim_variable;
			}

		}


		public static class HighwayDimensions {

			public static List<TimeOfDay> DefineTimeOfDay() {
				List<TimeOfDay> highway_times_of_day = new List<TimeOfDay>();
				highway_times_of_day.Add(new TimeOfDay("5to6", 300, 359));
				highway_times_of_day.Add(new TimeOfDay("6to7", 360, 419));
				highway_times_of_day.Add(new TimeOfDay("7to8", 420, 479));
				highway_times_of_day.Add(new TimeOfDay("8to9", 480, 539));
				highway_times_of_day.Add(new TimeOfDay("9to10", 540, 599));
				highway_times_of_day.Add(new TimeOfDay("10to14", 600, 839));
				highway_times_of_day.Add(new TimeOfDay("14to15", 840, 899));
				highway_times_of_day.Add(new TimeOfDay("15to16", 900, 959));
				highway_times_of_day.Add(new TimeOfDay("16to17", 960, 1019));
				highway_times_of_day.Add(new TimeOfDay("17to18", 1020, 1079));
				highway_times_of_day.Add(new TimeOfDay("18to20", 1080, 1199));
				highway_times_of_day.Add(new TimeOfDay("20to5", 1200, 299));
				return highway_times_of_day;
			}

			public static List<Mode> DefineModes() {
				List<Mode> highway_modes = new List<Mode>();
				highway_modes.Add(new Mode("sov", "highway", "sv"));
				highway_modes.Add(new Mode("hov2", "highway", "h2"));
				highway_modes.Add(new Mode("hov3", "highway", "h3"));
				return highway_modes;
			}

			public static List<PathType> DefinePathTypes() {
				List<PathType> highway_path_type = new List<PathType>();

				//for now it's pointing at the same network...
				highway_path_type.Add(new PathType("no-toll-network", "highway", "nt"));
				highway_path_type.Add(new PathType("full-network", "highway", "tl"));
				return highway_path_type;
			}

			public static List<ValueOfTime> DefineTollSOVValuesofTime() {
				List<ValueOfTime> highway_values_of_time = new List<ValueOfTime>();
				highway_values_of_time.Add(new ValueOfTime("very-low", 200, 1));
				highway_values_of_time.Add(new ValueOfTime("medium", 800, 2));
				highway_values_of_time.Add(new ValueOfTime("high", 2000, 3));
				return highway_values_of_time;
			}

			public static List<ValueOfTime> DefineTollHOVValuesofTime() {
				List<ValueOfTime> highway_values_of_time = new List<ValueOfTime>();
				highway_values_of_time.Add(new ValueOfTime("low", 400, 1));
				highway_values_of_time.Add(new ValueOfTime("high", 1500, 2));
				highway_values_of_time.Add(new ValueOfTime("very-high", 4000, 3));
				return highway_values_of_time;
			}


			public static List<ValueOfTime> DefineNoTollValuesofTime() {
				List<ValueOfTime> no_highway_values_of_time = new List<ValueOfTime>();
				no_highway_values_of_time.Add(new ValueOfTime("all", -1, 1));
				return no_highway_values_of_time;
			}

			public static List<SkimVariable> DefineSkimVariables() {
				List<SkimVariable> highway_skim_variable = new List<SkimVariable>();
				highway_skim_variable.Add(new SkimVariable("ivtime", "Time", "t", "distance"));
				highway_skim_variable.Add(new SkimVariable("distance", "Distance", "d", "distance"));
				highway_skim_variable.Add(new SkimVariable("toll", "Toll", "c", "distance"));
				return highway_skim_variable;
			}
		}


		public static class NonMotorizedDimensions {

			public static List<TimeOfDay> DefineTimesOfDay() {
				List<TimeOfDay> nonmotorized_times_of_day = new List<TimeOfDay>();
				//label 5 to 6 standing in for all day
				nonmotorized_times_of_day.Add(new TimeOfDay("5to6", 0, 1439));
				return nonmotorized_times_of_day;
			}

			public static List<Mode> DefineModes() {
				List<Mode> nonmotorized_modes = new List<Mode>();
				nonmotorized_modes.Add(new Mode("walk", "non_motorized"));
				nonmotorized_modes.Add(new Mode("bike", "non_motorized"));
				return nonmotorized_modes;
			}

			public static List<PathType> DefinePathTypes() {
				List<PathType> nonmotorized_path_type = new List<PathType>();
				nonmotorized_path_type.Add(new PathType("full-network", "non_motorized"));
				return nonmotorized_path_type;
			}

			public static List<ValueOfTime> DefineValuesofTime() {
			//These are fake we only want one value of time really, but I can't figure out
				//how to make the values of time mode specific
				List<ValueOfTime> nonmotorized_values_of_time = new List<ValueOfTime>();
				nonmotorized_values_of_time.Add(new ValueOfTime("all",-1, -1));
				return nonmotorized_values_of_time;
			}

			public static List<SkimVariable> DefineSkimVariables() {
				List<SkimVariable> nonmotorized_skim_variable = new List<SkimVariable>();
				nonmotorized_skim_variable.Add(new SkimVariable("time", "Time", "d", "distance"));
				nonmotorized_skim_variable.Add(new SkimVariable("distance", "Distance", "d", "distance"));

				return nonmotorized_skim_variable;
			}

		}



		public class RosterRecord {
			public string variable;
			public string mode;
			public string path_type;
			public string value_of_time_group;
			public int start_minute;
			public int end_minute;
			public string name;
			public string blend_var;
			public string factor;

			// these are the same for every record
			public int field = 1;
			public string file_type = "hdf5";
			public string blend_path_type = "null";
			//all values are scaled by 100 to be integers, so scaling is true.
			public string scaling = "TRUE";
			public string length = "maxzone";
			public string transpose = "FALSE";

			public RosterRecord(string variable, string mode, string path_type, string value_of_time_group,
				int start_minute, int end_minute, string name, string blend_var, string factor) {
				this.variable = variable;
				this.mode = mode;
				this.path_type = path_type;
				this.value_of_time_group = value_of_time_group;
				this.start_minute = start_minute;
				this.end_minute = end_minute;
				this.name = name;
				this.field = field;
				this.blend_var = blend_var;
				this.factor = factor;

			}



			public void Write() {


			}

		}

		public class TimeOfDay {
			public string time_name;
			public int start_time;
			public int end_time;

			public TimeOfDay(string time_name, int start_time, int end_time) {
				this.time_name = time_name;
				this.start_time = start_time;
				this.end_time = end_time;
			}

		}

		public class Mode {
			public string mode_name;
			public string parent_mode;
			public string emme_code;
			public string factor;

			public Mode(string mode_name, string parent_mode, string emme_code) {
				this.mode_name = mode_name;
				this.parent_mode = parent_mode;
				this.emme_code = emme_code;
				this.factor = "null";
			}

			public Mode(string mode_name, string parent_mode) {
				this.mode_name = mode_name;
				this.parent_mode = parent_mode;
				this.factor = "null";
			}

			//include a factor for speed in non-motorized
			public Mode(string mode_name, string parent_mode, double factor) {
				this.mode_name = mode_name;
				this.parent_mode = parent_mode;
				this.factor = factor.ToString();
			}

		}

	}

	public class PathType {
		public string path_type_name;
		public string mode;
		public string emme_code;

		public PathType(string path_type_name, string mode) {
			this.path_type_name = path_type_name;
			this.mode = mode;
		}

		public PathType(string path_type_name, string mode, string emme_code) {
			this.path_type_name = path_type_name;
			this.mode = mode;
			this.emme_code = emme_code;
		}

	}

	public class ValueOfTime {
		public string vot_name;
		public float dollars_per_hour;
		public int vot_id;

		public ValueOfTime(string vot_name, float dollars_per_hour, int vot_id) {
			this.vot_name = vot_name;
			this.dollars_per_hour = dollars_per_hour;
			this.vot_id = vot_id;
		}
	}
	public class SkimVariable {
		public string variable_name_roster;
		public string variable_name_in_file;
		public string variable_emme_code;
		public string blend_variable;

		public SkimVariable(string variable_name_roster, string variable_name_in_file, string variable_emme_code, string blend_variable) {
			this.variable_name_roster = variable_name_roster;
			this.variable_name_in_file = variable_name_in_file;
			this.variable_emme_code = variable_emme_code;
			this.blend_variable = blend_variable;
		}

		public SkimVariable(string variable_name_roster, string variable_name_in_file, string variable_emme_code) {
			this.variable_name_roster = variable_name_roster;
			this.variable_name_in_file = variable_name_in_file;
			this.variable_emme_code = variable_emme_code;
		}

	}
}







