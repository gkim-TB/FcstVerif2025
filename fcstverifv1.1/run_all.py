# fcstverif/run_all.py

import os
import sys
import subprocess
from pathlib import Path
import argparse

from fcstverif.config import VARIABLES, REGIONS, log_path

import logging
from fcstverif.src.utils.logging_utils import init_logger, get_logger

def run_script(script_name, var, region=None, debug=False, run_mode=None):
    base = Path(script_name).stem
    module_name = f"fcstverif.{base}"

    cmd = [sys.executable, "-m", module_name, "--var", var]
    if region:
        cmd += ["--region", region]
    if debug:
        cmd += ["--debug"]
    if run_mode is not None:
        cmd += ["--run_mode", run_mode]

    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env_py = env.get("PYTHONPATH", "")
    if str(repo_root) not in env_py.split(os.pathsep):
        env["PYTHONPATH"] = str(repo_root) + (os.pathsep + env_py if env_py else "")

    # not to make file handler by sub-process 
    env["FCSTVERIF_SUBPROCESS"] = "1"

    logger = logging.getLogger("fcstverif")
    logger.debug("Running subprocess: %s (cwd=%s)", " ".join(cmd), str(repo_root))

    # merge sub-process logger to main process (stdout+stdderr)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            cwd=str(repo_root),
                            env=env,
                            text=True, bufsize=1)

    try:
        # stamp to main logger 
        for line in proc.stdout:
            logger.info(line.rstrip())
    finally:
        if proc.stdout:
            proc.stdout.close()
    ret = proc.wait()
    if ret != 0:
        logger.error("Subprocess %s failed with returncode=%s", module_name, ret)
        raise subprocess.CalledProcessError(ret, cmd)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--var", help="단일 변수 또는 콤마구분 목록. 생략/ALL 이면 config.VARIABLES 사용", default=None)
    p.add_argument("--region", help="단일 지역 또는 콤마구분 목록. 생략/ALL 이면 config.REGIONS 사용", default=None)
    p.add_argument("--run_mode", choices=["manual","auto"], default=None)
    p.add_argument("--debug", action="store_true")
    return p.parse_args()

def main():
    init_logger(logfile=log_path, level=20, rotate=True, max_bytes=20*1024*1024, backup_count=10)
    logger = get_logger()
    logger.info("Start run_all")

    args = parse_args()
    vars_to_run = (VARIABLES if (not args.var or args.var.lower()=="all")
                   else [v.strip() for v in args.var.split(",") if v.strip()])
    regions_to_run = (list(REGIONS.keys()) if (not args.region or args.region.lower()=="all")
                      else [r.strip() for r in args.region.split(",") if r.strip()])
    logger.info(f"🔧 VARS={vars_to_run} | REGIONS={regions_to_run} | run_mode={args.run_mode or 'config default'}")

    for var in vars_to_run:
        
        logger.info(f"📦 [0] Preprocess... {var}")
        run_script("run_preprocessing.py", var, run_mode=args.run_mode, debug=args.debug)

        logger.info(f"📚 [1] Categorize... {var}")
        run_script("run_categorization.py", var, run_mode=args.run_mode, debug=args.debug)

        if var == 'sst':
            run_script("run_indices.py", var, run_mode=args.run_mode, debug=args.debug)

        for region in regions_to_run:
            logger.info(f"📊 [2] Analysis... {var}/{region}")
            run_script("run_analysis.py", var, region, run_mode=args.run_mode, debug=args.debug)

        for region in regions_to_run:
            logger.info(f"🖼️  [3] Plotting... {var}/{region}")
            run_script("run_plotting.py", var, region, run_mode=args.run_mode, debug=args.debug)

if __name__ == "__main__":
    main()
