#!/bin/bash
#SBATCH --job-name=game-stats-extractor
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem-per-cpu=1500M
#SBATCH --time=02:00:00
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

# Run extractor
echo "[$(date)] Running game-stats-extractor..."
game-stats-extractor \
    --replays-dir "${TMPDIR}/replays" \
    --map-data-dir "${TMPDIR}/static_maps" \
    --output "${TMPDIR}/stats" \
    --workers "${SLURM_CPUS_PER_TASK}"

# Copy results back to scratch
echo "[$(date)] Copying stats back to SCRATCH..."
rsync -aq --delete ${TMPDIR}/stats/ ${SCRATCH}/stats/

echo "[$(date)] Job finished!"
