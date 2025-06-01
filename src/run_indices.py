import argparse
from config import *
from src.analysis.calcIndices import calculate_indices

parser = argparse.ArgumentParser()
parser.add_argument("--var", required=True)
args = parser.parse_args()

calculate_indices(years=fyears)
