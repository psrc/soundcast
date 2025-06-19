from pathlib import Path
import toml
import os, sys

sys.path.append(os.path.join(os.getcwd(), 'scripts', 'summarize'))

from create_quarto_notebook import *

config = toml.load(os.path.join(os.getcwd(), "configuration/summary_configuration.toml"))


def main():

    # Ensure output directory for CSV outputs exists
    if not os.path.exists(os.path.join(os.getcwd(), "outputs/RTP")):
        os.makedirs(os.path.join(os.getcwd(),  "outputs/RTP"))
    for dir_name in ['person','mode_share','access']:
        if not os.path.exists(os.path.join(os.getcwd(), "outputs/RTP", dir_name)):
            os.makedirs(os.path.join(os.getcwd(), "outputs/RTP", dir_name))

    # create RTP summary notebook
    create_quarto_notebook(notebook_name = "RTP-summary-notebook",
                           summary_list = config["RTP_summary_list"],
                           scripts_dir = "scripts/summarize/RTP_summary",
                           output_folder = config["p_output_dir"])



if __name__ == "__main__":
    main()
