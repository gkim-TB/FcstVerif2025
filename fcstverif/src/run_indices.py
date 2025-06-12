import argparse
from config import *
from src.analysis.calcIndices import calculate_indices
from src.utils.general_utils import generate_yyyymm_list

parser = argparse.ArgumentParser()
parser.add_argument("--var", required=True)
args = parser.parse_args()
var = args.var
#model = args.model

fig_dir = os.path.join(output_fig_dir, 'IDX')
os.makedirs(fig_dir, exist_ok=True)
yyyymm_list = generate_yyyymm_list(year_start, year_end)

calculate_indices(
    var=var,
    yyyymm_list=yyyymm_list,
    model=model,
    fcst_dir=f'{model_out_dir}/anomaly',
    obs_dir=sst_out_dir,
    fig_dir=fig_dir)