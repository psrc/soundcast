import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import toml
import papermill as pm

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

def run_ipynb(input_settings,
              summary_settings,
              sheet_name: str, 
              nb_folder: Path):
    """Execute a Jupyter notebook using papermill."""

    print(f"Start executing {sheet_name}")
    start_time = time.time()
    nb_path = nb_folder / f"{sheet_name}.ipynb"
    
    input_config = input_settings.model_dump()
    summary_config = summary_settings.model_dump()
    
    pm.execute_notebook(
        str(nb_path),
        str(nb_path),  # Output to same file
        kernel_name=None,
        execution_timeout=1500,
        cwd=str(nb_folder),
        parameters=dict(summary_config = summary_config, # inject input and summary config as parameters
                        input_config = input_config)
    )

    end_time = time.time()
    print(f"Successfully executed {sheet_name} in {end_time - start_time:.1f} seconds")

def render_quarto(input_settings,
                  summary_settings,
                  notebook_name: str, 
                  scripts_dir: Path
                  ):

    print(f"Creating {notebook_name}...")

    nb_list = summary_settings.summary_list[notebook_name]

    for sheet_name in nb_list:
        run_ipynb(input_settings,
                  summary_settings,
                  sheet_name, 
                  scripts_dir/ "nb")

    # Render Quarto book using the same Python interpreter running this script.
    # This avoids Quarto picking up a different system Python that may not have
    # PyYAML/Jupyter installed.
    env = os.environ.copy()
    env["QUARTO_PYTHON"] = sys.executable

    result = subprocess.run(
        ["quarto", "render", str(scripts_dir)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Quarto render failed for "
            f"{notebook_name}.\n"
            f"QUARTO_PYTHON={env['QUARTO_PYTHON']}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
            "Ensure this Python environment has 'jupyter' and 'pyyaml' installed."
        )

    print(notebook_name + " created")

    output_summary_folder = PROJECT_ROOT / summary_settings.p_output_dir
    # create output folder if not exist
    output_summary_folder.mkdir(parents=True, exist_ok=True)
    # move notebook to output folder
    # Try to remove existing data first
    output_dir = output_summary_folder / notebook_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.move(scripts_dir / notebook_name, output_dir)


def create_quarto_notebooks(input_settings, summary_settings):
        
    # create RTP summary notebook
    if summary_settings.run_RTP_summary:

        render_quarto(input_settings,
                      summary_settings,
                      notebook_name = "RTP-summary-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/RTP_summary")
    
    # create validation notebook
    if summary_settings.run_validation:

        render_quarto(input_settings,
                      summary_settings,
                      notebook_name = f"{input_settings.abm_model}-validation-notebook",
                      scripts_dir = PROJECT_ROOT / f"scripts/summarize/validation_{input_settings.abm_model}")

    # create network validation notebook
    if summary_settings.run_network_validation:

        render_quarto(input_settings,
                      summary_settings,
                      notebook_name = "network-validation-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/validation_network")
                            
    # create comparison notebook
    if summary_settings.run_run_comparison:

        render_quarto(input_settings,
                      summary_settings,
                      notebook_name = "run-comparison-notebook",
                      scripts_dir = PROJECT_ROOT / "scripts/summarize/run_comparison") 


if __name__ == "__main__":
    from scripts.settings.state import InputSettings, SummarySettings

    # activitysim
    input_config = toml.load(PROJECT_ROOT / "configuration/asim_configuration/input_configuration.toml")
    summary_config = toml.load(PROJECT_ROOT / "configuration/asim_configuration/summary_configuration.toml")

    # daysim
    # input_config = toml.load(PROJECT_ROOT / "configuration/input_configuration.toml")
    # summary_config = toml.load(PROJECT_ROOT / "configuration/summary_configuration.toml")

    input_settings = InputSettings(**input_config)
    summary_settings = SummarySettings(**summary_config)

    create_quarto_notebooks(input_settings, summary_settings)
    