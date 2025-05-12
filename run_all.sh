# run_all.sh
#!/bin/bash
export PYTHONPATH=$(pwd)
export DISPLAY=:0

echo "[1] Preprocessing..."
python scripts/run_preprocessing.py

echo "[2] Analysis..."
python scripts/run_analysis.py

echo "[3] Plotting..."
python scripts/run_plotting.py

echo "✅ All done!"
