#!/bin/bash
#SBATCH --job-name=gnn-dataset-extractor
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --tmp=120g
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
echo "[$(date)] Copying training set to node-local storage..."
rsync -aq ${SCRATCH}/training_set/ ${TMPDIR}/training_set/

echo "[$(date)] Copying test set to node-local storage..."
rsync -aq ${SCRATCH}/test_set/ ${TMPDIR}/test_set/

echo "[$(date)] Copying map data to node-local storage..."
rsync -aq ${SCRATCH}/static_maps/ ${TMPDIR}/static_maps/

mkdir -p ${TMPDIR}/datasets/training ${TMPDIR}/datasets/evaluation ${TMPDIR}/graph_cache

# Build training dataset (one game_<id>.pt per replay)
echo "[$(date)] Extracting training dataset..."
gnn-extract build \
    --replays-dir "${TMPDIR}/training_set" \
    --maps-dir "${TMPDIR}/static_maps" \
    --output "${TMPDIR}/datasets/training" \
    --graph-cache-dir "${TMPDIR}/graph_cache" \
    --workers "${SLURM_CPUS_PER_TASK}"

# Build evaluation dataset
echo "[$(date)] Extracting evaluation dataset..."
gnn-extract build \
    --replays-dir "${TMPDIR}/test_set" \
    --maps-dir "${TMPDIR}/static_maps" \
    --output "${TMPDIR}/datasets/evaluation" \
    --graph-cache-dir "${TMPDIR}/graph_cache" \
    --workers "${SLURM_CPUS_PER_TASK}"

# Copy results back to scratch
echo "[$(date)] Copying datasets back to SCRATCH..."
rsync -aq ${TMPDIR}/datasets/ ${SCRATCH}/datasets/

echo "[$(date)] Job finished!"
