import os, sys, shutil, time
from pathlib import Path
import toml
import papermill as pm
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

# def run_ipynb(sheet_name, nb_folder: Path):
#     """Execute a Jupyter notebook using papermill."""

#     print(f"Start executing {sheet_name}")
#     start_time = time.time()
#     nb_path = nb_folder / f"{sheet_name}.ipynb"

#     pm.execute_notebook(
#         str(nb_path),
#         str(nb_path),  # Output to same file
#         kernel_name=None,
#         execution_timeout=1500,
#         cwd=str(nb_folder)
#     )

#     end_time = time.time()
#     print(f"Successfully executed {sheet_name} in {end_time - start_time:.1f} seconds")


def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    
    print("creating " + sheet_name + " page")
    with open(nb_path / (sheet_name + ".ipynb")) as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": nb_path}})
        with open(nb_path / (sheet_name + ".ipynb"), "wt") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print(f"Time taken to create {sheet_name} page: {end_time - start_time:.1f} seconds")


def render_quarto(
    notebook_name, 
    nb_list, 
    scripts_dir: Path, 
    output_summary_folder: Path
    ):

    for sheet_name in nb_list:
        run_ipynb(sheet_name, scripts_dir/ "nb")

    # render quarto book
    text = "quarto render " + str(scripts_dir)
    os.system(text)
    print(notebook_name + " created")

    # create output folder if not exist
    output_summary_folder.mkdir(parents=True, exist_ok=True)
    # move notebook to output folder
    # Try to remove existing data first
    output_dir = output_summary_folder / notebook_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.move(scripts_dir / notebook_name, output_dir)


def create_quarto_notebooks(abm_model, summary_settings):

    # run notebooks
    run_RTP_summary = summary_settings.run_RTP_summary
    run_validation = summary_settings.run_validation
    run_network_validation = summary_settings.run_network_validation
    run_comparison = summary_settings.run_run_comparison

    output_path = Path.cwd()/ summary_settings.p_output_dir

        
    # create RTP summary notebook
    if run_RTP_summary:
        render_quarto(notebook_name = "RTP-summary-notebook",
                            nb_list = summary_settings.rtp_summary_list,
                            scripts_dir = Path.cwd()/ "scripts/summarize/RTP_summary",
                            output_summary_folder = output_path)
    
    # create validation notebook
    if run_validation:
        
        if abm_model == "daysim":
            validation_nb_list = summary_settings.validation_list_daysim
        elif abm_model == "activitysim":
            validation_nb_list = summary_settings.validation_list_activitysim

        render_quarto(notebook_name = f"{abm_model}-validation-notebook",
                            nb_list = validation_nb_list,
                            scripts_dir = Path.cwd()/ f"scripts/summarize/validation_{abm_model}",
                            output_summary_folder = output_path)

    # create network validation notebook
    if run_network_validation:
        render_quarto(notebook_name = "network-validation-notebook",
                            nb_list = summary_settings.network_validation_list,
                            scripts_dir = Path.cwd()/ "scripts/summarize/validation_network",
                            output_summary_folder = output_path)
                            
    # create comparison notebook
    if run_comparison:
        render_quarto(notebook_name = "run-comparison-notebook",
                            nb_list = summary_settings.comparison_summary_list,
                            scripts_dir = Path.cwd()/ "scripts/summarize/run_comparison",
                            output_summary_folder = output_path) 


if __name__ == "__main__":
    
    sys.path.append(os.getcwd())
    from scripts.settings.state import InputSettings, SummarySettings

    
    config = toml.load(Path.cwd() / "configuration/input_configuration.toml")
    summary_config = toml.load(
        Path.cwd() / "configuration/summary_configuration.toml"
    )

    input_settings = InputSettings(**config)
    summary_settings = SummarySettings(**summary_config)

    create_quarto_notebooks(input_settings.abm_model, summary_settings)
    