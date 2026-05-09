import os, sys, shutil, time
from pathlib import Path
import toml
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

config = toml.load(Path.cwd() / "configuration/summary_configuration.toml")
valid_config = toml.load(Path.cwd() / "configuration/validation_configuration.toml")

# run notebooks
run_comparison = config['run_run_comparison']
run_RTP_summary = config['run_RTP_summary']
run_network_validation = valid_config['run_network_validation']
run_validation = valid_config['run_validation']


def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    print("creating " + sheet_name + " page")
    with open(Path(nb_path) / (sheet_name + ".ipynb")) as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": Path(nb_path)}})
        with open(Path(nb_path) / (sheet_name + ".ipynb"), "wt") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print(f"Time taken to create {sheet_name} page: {end_time - start_time:.1f} seconds")


def create_quarto_notebook(notebook_name, summary_list, scripts_dir, output_folder):

    for sheet_name in summary_list:
        run_ipynb(sheet_name, scripts_dir + "/summary_scripts")

    # render quarto book
    # TODO: automate _quarto.yml chapter list
    text = "quarto render " + scripts_dir
    os.system(text)
    print(notebook_name + " created")

    # Try to remove existing data first
    output_dir = Path.cwd() / output_folder / notebook_name
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    # Move these files to output folder
    if not os.path.exists(Path.cwd() / output_folder):
        os.makedirs(Path.cwd() / output_folder)
    shutil.move(Path.cwd() / scripts_dir / notebook_name, output_dir)

def main():

    # create summary notebook
    if run_comparison:
        create_quarto_notebook(notebook_name = "run-comparison-notebook",
                            summary_list = config["summary_list"],
                            scripts_dir = "scripts/summarize/summary",
                            output_folder = config["p_output_dir"]) 
        
    # create RTP summary notebook
    if run_RTP_summary:
        create_quarto_notebook(notebook_name = "RTP-summary-notebook",
                            summary_list = config["RTP_summary_list"],
                            scripts_dir = "scripts/summarize/RTP_summary",
                            output_folder = config["p_output_dir"])

    # create network validation notebook
    if run_network_validation:
        create_quarto_notebook(notebook_name = "network-validation-notebook",
                            summary_list = valid_config["network_summary_list"],
                            scripts_dir = "scripts/summarize/validation_network",
                            output_folder = valid_config["p_output_dir"])
    
    # create validation notebook
    if run_validation:
        create_quarto_notebook(notebook_name = "validation-notebook",
                            summary_list = valid_config["summary_list"],
                            scripts_dir = "scripts/summarize/validation",
                            output_folder = valid_config["p_output_dir"])

        # separate notebook for telecommute analysis
        if "../telecommute_analysis/telecommute_analysis" in valid_config["summary_list"]:
            # Try to remove existing data first
            telecommute_analysis_output_dir = Path.cwd() / valid_config["p_output_dir"] / "telecommute-analysis-notebook"
            if os.path.exists(telecommute_analysis_output_dir):
                shutil.rmtree(telecommute_analysis_output_dir)

            text = "quarto render scripts/summarize/validation/telecommute_analysis"
            os.system(text)
            print("telecommute analysis notebook created")

            # Move these files to output folder
            if not os.path.exists(Path.cwd() / valid_config["p_output_dir"]):
                os.makedirs(Path.cwd() / valid_config["p_output_dir"])
            shutil.move(
                Path.cwd() / "scripts/summarize/validation/telecommute-analysis-notebook",
                telecommute_analysis_output_dir,
            )

if __name__ == "__main__":
    main()