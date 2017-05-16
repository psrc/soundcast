import argparse, os, sys, fnmatch
import tables
import numpy as np
import inro.emme.matrix as ematrix
import inro.emme.database.emmebank as ebank
import re
import json
from datetime import datetime, timedelta

# Being bad and setting a global compression variable for HDF5
# stores
filters = tables.Filters(complevel=1, complib='zlib')

converted = 0
num_to_convert = 0
start = 0

def emmemat2np(emmefullmatrix, dtype=np.float32):
    """
    Converts an emmematrix object into a numpy matrix
    """
    mat = emmefullmatrix.get_data()
    npmat = mat.to_numpy()
   
    return(npmat)

def convert_fullmats(srcbankpath, h5filepath, h5grouppath=None, mats=None, dryrun=False):
    """
    Converts the full matrices in an Emmebank and stores them in an
    HDF5 file. Optionally specify the destination group and a list of
    matrices to convert. By default, creates a destination group with
    the name of the emmebank and converts all matrices.
    """

    global num_to_convert, converted, start

    # Context managers work with Emme 4.0.8 or newer, otherwise the
    # 'with' keyword fails on Emmebank()
    # Sadly, opening multiple files in a single un-nested with block
    # was added in Python 2.7, and so this is a little nesty.
    # See: http://goo.gl/ucEsR for details.
    with ebank.Emmebank(srcbankpath) as srcbank:
        h5grouppath = h5grouppath or "/" + re.sub('[^0-9a-zA-Z]+',
                                                  '', srcbank.title)

        # Hacky work-around for Emmebanks that were created with an
        # error-producing scenario 9999. According to Chris J.,
        # sometimes scenario 9999 is bogus and should be removed, but
        # sometimes is not. This is a crude heuristic, and it would be
        # better to do some clean-up in the model.
        sn = [x.number for x in srcbank.scenarios()]
        if len(sn) > 1 and 9999 in sn:
            try:
                srcbank.delete_scenario(9999)
            except:
                pass
         
        with tables.File(h5filepath, mode="a", filters=filters) as h5file:
            for mat in srcbank.matrices():
                full_mat_name = h5grouppath+'/'+mat.name
                if full_mat_name not in mats:
                    pass
                else:
                    if dryrun:
                        print "%s/%s" % (h5grouppath,mat.name),
                    else:
                        print("Converting: %s/%s\n         -> %s/%s"
                               % (srcbankpath, mat.name, h5grouppath, mat.name))

                    group = get_or_create_group(h5file, h5grouppath)
                    

                    if not dryrun:
                        a = h5file.create_array(h5grouppath,
                                               mat.name,
                                               emmemat2np(mat))
                        a.attrs.description = mat.description

                    # Housekeeping
                    converted += 1
                    mats.remove(full_mat_name)

                    now = datetime.now()
                    fraction = 1.0 * converted / num_to_convert
                    time_so_far = now - start

                    seconds_so_far = time_so_far.seconds
                    total_estimate = 1.0 * seconds_so_far / fraction
                    seconds_left = total_estimate - seconds_so_far
                    time_left = timedelta(seconds=seconds_left)

                    if not dryrun:
                        print "            Finished %d of %d. Estimated time remaining: %s\n" % (
                                           converted, num_to_convert, time_left)


def get_or_create_group(h5file, h5grouppath):
    try:
        group = h5file.getNode(h5grouppath)
        return group
    except:
        pass

    #If we're here, the group doesn't exist.  Create it.

    paths = filter(lambda x: x != "", h5grouppath.split("/"))
    base = "/"
    

    for x in paths:
        try:
            h5file.create_group(base, x)
        except:
            pass
        base = base + "/" + x



def get_matrix_defs_from_json(json_file):
    with file(json_file) as jfile:
        config = json.load(jfile)

    matrices = set()

    # Benefits by Period:
    for per in config["timeperiods"]["periods"]:
        period = per["period"]
        code = per["code"]
        trperiod = per["trperiod"]
        trcode = per["trcode"]
        assignper = per["assignper"]
        fareper = per["fareper"]
        distper = per["distper"]
        walkper = per["walkper"]
        bikeper = per["bikeper"]


        for zzben in config["benefits-by-period"]:
            cp = zzben["costpath"]
            vp = zzben["volumepath"]

            # Substitute various time period placeholders
            cp = cp.replace("${PER}",period)
            cp = cp.replace("${CODE}",code)
            cp = cp.replace("${TRPER}",trperiod)
            cp = cp.replace("${TRCODE}",trcode)
            cp = cp.replace("${ASSIGNPER}",assignper)
            cp = cp.replace("${FAREPER}",fareper)
            cp = cp.replace("${DISTPER}",distper)
            cp = cp.replace("${WALKPER}",walkper)
            cp = cp.replace("${BIKEPER}",bikeper)

            vp = vp.replace("${PER}",period)
            vp = vp.replace("${CODE}",code)
            vp = vp.replace("${TRPER}",trperiod)
            vp = vp.replace("${TRCODE}",trcode)
            vp = vp.replace("${ASSIGNPER}",assignper)
            vp = vp.replace("${FAREPER}",fareper)
            vp = vp.replace("${DISTPER}",distper)
            vp = vp.replace("${WALKPER}",walkper)
            vp = vp.replace("${BIKEPER}",bikeper)

            matrices.add(cp)
            matrices.add(vp)

    return matrices


def find_all_emmebanks(root):
    emmebanks = []

    for path,names,files in os.walk(root):
        for filename in fnmatch.filter(files,'emmebank'):
            emmebanks.append(os.path.join(path,filename))

    return emmebanks



if __name__ == '__main__':
    # Set up our command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--append",
                        help="Append output to existing HDF5 file",
                        action="store_true")

    parser.add_argument("outputfile",
                        help='''HDF5 file for output,
                        will not overwrite existing''')

    parser.add_argument("jsonfile",
                        help='''JSON config file for BC2''')

    parser.add_argument("inputfolder",
                        help="Specify root folder containing emmebanks for conversion")

    args = parser.parse_args()

    if args.append==False and os.path.isfile(args.outputfile):
        raise IOError("Output file exists. Not overwriting.")

    # Fetch the matrix definitions we'll need to import
    matrices = get_matrix_defs_from_json(args.jsonfile)
    num_to_convert = len(matrices)

    # Recursively find all the emmebanks in the root folder
    emmebanks = find_all_emmebanks(args.inputfolder)

    # Check to see if all specified matrices exist in an emmebank somewhere
    print "Finding matrices in emmebanks:"
    start = datetime.now()
    for bank in emmebanks:
        convert_fullmats(bank, args.outputfile, mats=matrices, dryrun=True)

    if len(matrices)>0:
        print "\n\n*** %d MATRICES MISSING ***" % len(matrices)
        for m in sorted(matrices):
            print "   "+m
        #sys.exit(2)

    # Convert all matrices we need, from all matrices available
    start = datetime.now()
    converted = 0
    matrices = get_matrix_defs_from_json(args.jsonfile)

    for bank in emmebanks:
        convert_fullmats(bank, args.outputfile, mats=matrices)

    print "Completed in",datetime.now()-start

