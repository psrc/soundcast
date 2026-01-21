import subprocess
from emme_project import EmmeProject

activitysim_uvenv_path = r"C:\workspace\asim_uv\.venv\Scripts\python.exe"
emme_project_path = (
    r"C:\workspace\sc_uv_test\soundcast\projects\LoadTripTables\LoadTripTables.emp"
)

print("Opeining Emme project using Soundcast uv venv...")
my_project = EmmeProject(emme_project_path)

print("Running activitysim using activitysim uv venv...")
subprocess.run(
    [
        activitysim_uvenv_path,
        "-m",
        "activitysim",
        "run",
        "-c",
        r"C:\workspace\activitysim_dir\psrc_activitysim_pre_tele\psrc_activitysim\configs_sh",
        "-c",
        r"C:\workspace\activitysim_dir\psrc_activitysim_pre_tele\psrc_activitysim\configs_mp",
        "-c",
        r"C:\workspace\activitysim_dir\psrc_activitysim_pre_tele\psrc_activitysim\configs_dev",
        "-o",
        r"C:\workspace\activitysim_dir\outputs\test",
        "-d",
        r"C:\workspace\activitysim_dir\2023\data_full",
    ]
)

print("Switching active database in Emme uing Soundcat uv venv...")
my_project.change_active_database("7to8")
print("Done!")
