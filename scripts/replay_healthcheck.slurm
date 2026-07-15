#!/bin/bash
#SBATCH --job-name=replay-healthcheck
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem-per-cpu=2G
#SBATCH --time=04:00:00
#SBATCH --tmp=100g
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -e

echo "[$(date)] Job started on $(hostname)"

# Load Python
echo "[$(date)] Loading modules..."
module load stack/2024-06
module load python/3.12.8

# Activate environment
echo "[$(date)] Activating virtual environment..."
cd $HOME/conlyse
source venv/bin/activate

# Copy input data to node-local storage
echo "[$(date)] Copying replays to node-local storage..."
rsync -aq ${SCRATCH}/replays/ ${TMPDIR}/replays/

echo "[$(date)] Copying map data to node-local storage..."
rsync -aq ${SCRATCH}/static_maps/ ${TMPDIR}/static_maps/

# Run health check
echo "[$(date)] Running replay_healthcheck..."
python scripts/replay_healthcheck/__main__.py \
    --replays-dir "${TMPDIR}/replays" \
    --map-data-dir "${TMPDIR}/static_maps" \
    --workers "${SLURM_CPUS_PER_TASK}" \
    --output-dir "${TMPDIR}/health_report"

# Copy the HTML + JSON reports back to scratch
echo "[$(date)] Copying health report back to SCRATCH..."
mkdir -p "${SCRATCH}/replay_health_reports/${SLURM_JOB_ID}"
rsync -aq "${TMPDIR}/health_report/" "${SCRATCH}/replay_health_reports/${SLURM_JOB_ID}/"

echo "[$(date)] Job finished!"
