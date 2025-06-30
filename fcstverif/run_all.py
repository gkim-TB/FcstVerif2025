# fcstverif/run_all.py

import subprocess
import os
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
    
    subprocess.run(cmd, check=True, cwd=os.getcwd(), env=dict(os.environ, PYTHONPATH=os.getcwd()))

def main():
    
    for var in VARIABLES:
        
        print("📦 [1] Preprocessing...")
        print(f"\n🔧 Processing: var={var}, region=GL")
        run_script("run_preprocessing.py", var)

        run_script("run_categorization.py", var)

        if var == 'sst':
            run_script("run_indices.py", var)

        for region in REGIONS:
            print("📊 [2] Analysis...")
            run_script("run_analysis.py", var, region)

        for region in REGIONS:
            print("🖼️  [3] Plotting...")
            run_script("run_plotting.py", var, region)

if __name__ == "__main__":
    main()