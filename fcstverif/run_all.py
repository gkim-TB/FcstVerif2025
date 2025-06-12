# scripts/run_all.py
# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import subprocess
import os
from fcstverif.config import variables, REGIONS

def run_script(script_path, var, region=None):
    cmd = ["python", script_path, "--var", var]
    if region:
        cmd += ["--region", region]
    subprocess.run(cmd, check=True, cwd=os.getcwd(), env=dict(os.environ, PYTHONPATH=os.getcwd()))

def main():
    for var in variables:
        
        print("📦 [1] Preprocessing...")
        print(f"\n🔧 Processing: var={var}, region=GL")
        run_script("src/run_preprocessing.py", var)

        run_script("src/run_categorization.py", var)

        if var == 'sst':
            run_script("src/run_indices.py", var)

        # analysis/plotting 분리해서 디버깅 효율 챙겨
        for region in REGIONS:
             print("📊 [2] Analysis...")
             run_script("src/run_analysis.py", var, region)
        del region

        for region in REGIONS:
            print("🖼️  [3] Plotting...")
            run_script("src/run_plotting.py", var, region)

if __name__ == "__main__":
    main()
