import argparse


def add_run_args(parser, multiprocess=True):
    """
    Run command args
    """
    parser.add_argument(
        "-c", "--configs_dir", type=str, metavar="PATH", help="path to configs dir"
    )

    parser.add_argument(
        "-o", "--output_dir", type=str, metavar="PATH", help="path to output dir"
    )

    parser.add_argument(
        "-d", "--data_dir", type=str, metavar="PATH", help="path to data dir"
    )

    


# if __name__ == '__main__':
parser = argparse.ArgumentParser()
add_run_args(parser)
args = parser.parse_args()
