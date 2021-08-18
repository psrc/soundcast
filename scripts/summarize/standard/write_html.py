import os, sys, shutil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),r"scripts/summarize/notebooks"))
sys.path.append(os.getcwd())
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from input_configuration import model_year, base_year
from settings import run_comparison


def write_nb(sheet_name, nb_path, output_path):

    #try:
    with open(nb_path+r'/'+sheet_name+".ipynb") as f:
        nb = nbformat.read(f, as_version=4)
        if (sys.version_info > (3, 0)):
            py_version = 'python3'
        else:
            py_version = 'python2'
        ep = ExecutePreprocessor(timeout=600, kernel_name=py_version)
        ep.preprocess(nb, {'metadata': {'path': nb_path+r'/'}})
        with open(nb_path+r'/'+sheet_name+".ipynb", 'wt') as f:
            nbformat.write(nb, f)
        if (sys.version_info > (3, 0)):
            text = "jupyter nbconvert --to HTML --TemplateExporter.exclude_input=True "+nb_path+r'//'+sheet_name+".ipynb"
            os.system(text)
        else:
            text = "jupyter nbconvert --to HTML "+nb_path+r'//'+sheet_name+".ipynb"
            os.system(text)

        # Move these files to output
        ext = '.html'
        if os.path.exists(os.path.join(os.getcwd(),output_path,sheet_name+ext)):
            os.remove(os.path.join(os.getcwd(),output_path,sheet_name+ext))
        os.rename((os.path.join(nb_path,sheet_name+ext)), os.path.join(os.getcwd(),output_path,sheet_name+ext))
    #except:
    #   print('unable to produce '+sheet_name)

def main():

    # Create HTML sheets from jupyter notebooks
    # Run all RTP summaries and generate comparison notebook inputs
    for geog in ['city','county', 'rg','topsheet','poc','lowinc','rgc']:
        dirname = os.path.join(os.getcwd(),'outputs/compare',geog)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        write_nb(geog+'_summary', "scripts/summarize/notebooks", r'outputs')
        if run_comparison:
            write_nb('compare_results_'+geog, "scripts/summarize/notebooks", r'outputs/compare')
    for geog in ['county','rg','rgc','city']:
        write_nb(geog+'_network_summary', "scripts/summarize/notebooks", r'outputs')
        

    write_nb('metrics', "scripts/summarize/notebooks", r'outputs/')
    
    # write validation notebooks
    for sheet_name in ['auto_ownership','bike_validation','day_pattern','daysim_overview',
                        'intermediate_stop_generation','school_location',
                        'time_choice','tour_destination','tour_distance',
                        'tour_mode','trip_destination','trip_mode',
                        'validation','work_at_home','work_location']:
        write_nb(sheet_name, "scripts/summarize/notebooks/validation", r'outputs/validation/')

if __name__ == '__main__':
    main()