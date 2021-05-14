import os, sys, shutil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from input_configuration import model_year, base_year

def write_nb(sheet_name, nb_path, output_path):

    with open(nb_path+r'/'+sheet_name+".ipynb") as f:
        nb = nbformat.read(f, as_version=4)
        if (sys.version_info > (3, 0)):
            py_version = 'python3'
        else:
            py_version = 'python2'
        ep = ExecutePreprocessor(timeout=600, kernel_name=py_version)
        ep.preprocess(nb, {'metadata': {'path': nb_path+r'/'}})
        with open(sheet_name+'.ipynb', 'wt') as f:
            nbformat.write(nb, f)
        if (sys.version_info > (3, 0)):
            os.system("jupyter nbconvert --to HTML --TemplateExporter.exclude_input=True "+nb_path+r'//'+sheet_name+".ipynb")
        else:
            os.system("jupyter nbconvert --to HTML "+nb_path+r'//'+sheet_name+".ipynb")
        # Move these files to output
        if os.path.exists(os.path.join(os.getcwd(),output_path,sheet_name+".html")):
            os.remove(os.path.join(os.getcwd(),output_path,sheet_name+".html"))
        os.rename((os.path.join(nb_path,sheet_name+".html")), os.path.join(os.getcwd(),output_path,sheet_name+".html"))

def main():

    # Create HTML sheets from jupyter notebooks
    #for sheet_name in ['topsheet','metrics','work']:
    #    write_nb(sheet_name, "scripts/summarize/notebooks", r'outputs/')
    
    # write validation notebook if running base year
    if str(model_year)==str(base_year):
        for sheet_name in ['validation','daysim','census','school_location','work_location','tour_distance','tour']:
            write_nb(sheet_name, "scripts/summarize/notebooks/validation", r'outputs/validation/')


if __name__ == '__main__':
    main()