from pathlib import Path
import toml
import os, sys

sys.path.append(os.path.join(os.getcwd(), 'scripts', 'summarize'))

from create_quarto_notebook import *

config = toml.load(os.path.join(os.getcwd(), "configuration/validation_configuration.toml"))



def main():

    # create validation notebook
    create_quarto_notebook(notebook_name = "validation-notebook",
                           summary_list = config["summary_list"],
                           scripts_dir = "scripts/summarize/validation",
                           output_folder = config["p_output_dir"])
    

    ## separate notebook for telecommute analysis
    if "../telecommute_analysis/telecommute_analysis" in config["summary_list"]:
        # Try to remove existing data first
        telecommute_analysis_output_dir = os.path.join(os.getcwd(), config["p_output_dir"], "telecommute-analysis-notebook")
        if os.path.exists(telecommute_analysis_output_dir):
            shutil.rmtree(telecommute_analysis_output_dir)

        text = "quarto render scripts/summarize/validation/telecommute_analysis"
        os.system(text)
        print("telecommute analysis notebook created")

        # Move these files to output folder
        if not os.path.exists(os.path.join(os.getcwd(), config["p_output_dir"])):
            os.makedirs(os.path.join(os.getcwd(), config["p_output_dir"]))
        shutil.move(
            os.path.join(os.getcwd(), "scripts/summarize/validation/telecommute-analysis-notebook"),
            telecommute_analysis_output_dir,
        )


if __name__ == "__main__":
    main()
