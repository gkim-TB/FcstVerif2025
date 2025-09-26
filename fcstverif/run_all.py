# fcstverif/run_all.py

import subprocess
import os
import argparse
from fcstverif.config import VARIABLES, REGIONS

def run_script(script_name, var, region=None, debug=False, run_mode=None):
    # src/ 디렉토리 내의 스크립트 경로 구성
    script_full_path = os.path.join(os.path.dirname(__file__), script_name)
    cmd = ["python", script_full_path, "--var", var]
    if region:
        cmd += ["--region", region]
    if debug:
        cmd += ["--debug"]
    if run_mode is not None:
        cmd += ["--run_mode", run_mode]
    
    subprocess.run(cmd, check=True) #, cwd=os.getcwd(), env=dict(os.environ, PYTHONPATH=os.getcwd()))

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--var", help="단일 변수 또는 콤마구분 목록. 생략/ALL 이면 config.VARIABLES 사용", default=None)
    p.add_argument("--region", help="단일 지역 또는 콤마구분 목록. 생략/ALL 이면 config.REGIONS 사용", default=None)
    p.add_argument("--run_mode", choices=["manual","auto"], default=None)
    p.add_argument("--debug", action="store_true")
    return p.parse_args()

def main():
    args = parse_args()

    vars_to_run = (VARIABLES if (not args.var or args.var.lower()=="all")
                   else [v.strip() for v in args.var.split(",") if v.strip()])
    regions_to_run = (REGIONS if (not args.region or args.region.lower()=="all")
                      else [r.strip() for r in args.region.split(",") if r.strip()])
    print(f"🔧 VARS={vars_to_run} | REGIONS={regions_to_run} | run_mode={args.run_mode or 'config default'}")

    for var in vars_to_run:
        
        print(f"📦 [0] Preprocess... {var}")
        run_script("run_preprocessing.py", var)

        print(f"📦 [1] Categorize... {var}")
        run_script("run_categorization.py", var)

        if var == 'sst':
            run_script("run_indices.py", var)

        for region in REGIONS:
            print(f"📊 [2] Analysis... {var}/{region}")
            run_script("run_analysis.py", var, region)

        for region in REGIONS:
            print(f"🖼️  [3] Plotting... {var}/{region}")
            run_script("run_plotting.py", var, region)

if __name__ == "__main__":
    main()