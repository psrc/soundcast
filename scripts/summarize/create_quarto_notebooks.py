import os
import shutil
import sys
import time
from pathlib import Path
import toml
import papermill as pm

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

def run_ipynb(input_settings: dict,
              summary_settings: dict,
              sheet_name: str, 
              nb_folder: Path):
    """Execute a Jupyter notebook using papermill."""

    print(f"Start executing {sheet_name}")
    start_time = time.time()
    nb_path = nb_folder / f"{sheet_name}.ipynb"
    
    pm.execute_notebook(
        str(nb_path),
        str(nb_path),  # Output to same file
        kernel_name=None,
        execution_timeout=1500,
        cwd=str(nb_folder),
        parameters=dict(summary_config = summary_settings, # inject input and summary config as parameters
                        input_config = input_settings)
    )

    end_time = time.time()
    print(f"Successfully executed {sheet_name} in {end_time - start_time:.1f} seconds")

def  render_quarto(input_settings: dict,
                   summary_settings: dict,
                   notebook_name: str, 
                   scripts_dir: Path):

    print(f"Creating {notebook_name}...")

    nb_list = summary_settings["summary_list"][notebook_name]

    for sheet_name in nb_list:
        run_ipynb(input_settings,
                  summary_settings,
                  sheet_name, 
                  scripts_dir/ "nb")

    # render quarto book
    text = "quarto render " + str(scripts_dir)
    os.system(text)
    print(notebook_name + " created")

    output_summary_folder = Path(summary_settings['output_dir']) / "summary"
    # create output folder if not exist
    output_summary_folder.mkdir(parents=True, exist_ok=True)
    # move notebook to output folder
    # Try to remove existing data first
    notebook_output_dir = output_summary_folder / notebook_name
    if notebook_output_dir.exists():
        shutil.rmtree(notebook_output_dir)
    shutil.move(scripts_dir / notebook_name, notebook_output_dir)


def create_quarto_notebooks(input_settings, summary_settings, run_args=None):

    # convert pydantic model to dict
    input_config = input_settings.model_dump()
    summary_config = summary_settings.model_dump()
    
    # for activitysim runs: add output_dir and data_dir from run_args to summary_config if provided
    if run_args:
        run_args_obj = getattr(run_args, "args", run_args)
        output_dir = getattr(run_args_obj, "output_dir", None)
        data_dir = getattr(run_args_obj, "data_dir", None)

        # add output_dir and data_dir to summary_config disctionary
        summary_config["output_dir"] = output_dir
        summary_config["data_dir"] = data_dir

    # create RTP summary notebook
    if summary_config['run_RTP_summary']:

        render_quarto(input_config,
                      summary_config,
                      notebook_name = "RTP-summary-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/RTP_summary")
    
    # create validation notebook
    if summary_config['run_validation']:

        render_quarto(input_config,
                      summary_config,
                      notebook_name = f"{input_config['abm_model']}-validation-notebook",
                      scripts_dir = PROJECT_ROOT / f"scripts/summarize/validation_{input_config['abm_model']}")

    # create network validation notebook
    if summary_config['run_network_validation']:

        render_quarto(input_config,
                      summary_config,
                      notebook_name = "network-validation-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/validation_network")
                            
    # create comparison notebook
    if summary_config['run_run_comparison']:

        render_quarto(input_config,
                      summary_config,
                      notebook_name = "run-comparison-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/run_comparison") 


if __name__ == "__main__":

    import argparse
    from scripts.settings.state import InputSettings, SummarySettings

    # daysim
    # input_config = toml.load(PROJECT_ROOT / "configuration/input_configuration.toml")
    # summary_config = toml.load(PROJECT_ROOT / "configuration/summary_configuration.toml")

    # activitysim
    input_config = toml.load(PROJECT_ROOT / "configuration/asim_configuration/input_configuration.toml")
    summary_config = toml.load(PROJECT_ROOT / "configuration/asim_configuration/summary_configuration.toml")

    # Example run_args object
    run_args = argparse.Namespace(
        args=argparse.Namespace(
            output_dir="P:/workspace/sc_6_22_26_asim_output",
            data_dir="P:/workspace/sc_6_22_26_asim_data",
        )
    )

    input_settings = InputSettings(**input_config)
    summary_settings = SummarySettings(**summary_config)

    create_quarto_notebooks(input_settings, summary_settings, run_args)
    