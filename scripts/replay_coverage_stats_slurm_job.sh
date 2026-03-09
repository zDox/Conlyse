#!/bin/bash
#SBATCH --job-name=replay_coverage_stats
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=2G
#SBATCH --output=replay_coverage_%j.out
#SBATCH --error=replay_coverage_%j.err

set -e

echo "[$(date)] Job started on $(hostname)"

# Load Python
echo "[$(date)] Loading modules..."
module load stack/2024-06
module load python/3.12.8

# Activate environment
echo "[$(date)] Activating virtual environment..."
cd "$HOME/conlyse"
source venv/bin/activate


# Run coverage stats on the replay output directory on SCRATCH
REPLAY_DIR="${SCRATCH}/replays_out"
OUTPUT_DIR="${SCRATCH}/replay_coverage_stats"
SUMMARY_JSON="${OUTPUT_DIR}/summary.json"

mkdir -p "${OUTPUT_DIR}"

cd "$HOME/conlyse/ConflictInterface"

echo "[$(date)] Running replay coverage statistics..."
python tools/replay_coverage_stats.py \
  "${REPLAY_DIR}" \
  --pattern "*" \
  --max-gap-minutes 60 \
  --output-dir "${OUTPUT_DIR}" \
  --summary-json "${SUMMARY_JSON}" \
  --jobs "${SLURM_CPUS_PER_TASK:-1}"

echo "[$(date)] Job finished!"

