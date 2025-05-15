# scripts/run_all.py

import subprocess
import os
from fcstverif.config import variables, REGIONS

def run_script(script_path, var, region):
    cmd = ["python", script_path, "--var", var, "--region", region]
    subprocess.run(cmd, check=True, cwd=os.getcwd(), env=dict(os.environ, PYTHONPATH=os.getcwd()))

def main():
    for var in variables:
        for region in REGIONS:
            print(f"\n🔧 Processing: var={var}, region={region}")

            print("📦 [1] Preprocessing...")
            run_script("scripts/run_preprocessing.py", var, region)

            print("📊 [2] Analysis...")
            run_script("scripts/run_analysis.py", var, region)

            print("🖼️  [3] Plotting...")
            run_script("scripts/run_plotting.py", var, region)

if __name__ == "__main__":
    main()
