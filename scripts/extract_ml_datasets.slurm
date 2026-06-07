#!/bin/bash
#SBATCH --job-name=ml-dataset-extractor
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=96G
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
echo "[$(date)] Copying training set to node-local storage..."
rsync -aq ${SCRATCH}/training_set/ ${TMPDIR}/training_set/

echo "[$(date)] Copying test set to node-local storage..."
rsync -aq ${SCRATCH}/test_set/ ${TMPDIR}/test_set/

echo "[$(date)] Copying map data to node-local storage..."
rsync -aq ${SCRATCH}/static_maps/ ${TMPDIR}/static_maps/

mkdir -p ${TMPDIR}/datasets

# Build training dataset
echo "[$(date)] Extracting training dataset..."
game-stats-extractor ml-dataset \
    --replays-dir "${TMPDIR}/training_set" \
    --map-data-dir "${TMPDIR}/static_maps" \
    --output "${TMPDIR}/datasets/training.parquet" \
    --workers "${SLURM_CPUS_PER_TASK}" \
    --min-bucket-coverage 2

# Build evaluation dataset
echo "[$(date)] Extracting evaluation dataset..."
game-stats-extractor ml-dataset \
    --replays-dir "${TMPDIR}/test_set" \
    --map-data-dir "${TMPDIR}/static_maps" \
    --output "${TMPDIR}/datasets/evaluation.parquet" \
    --workers "${SLURM_CPUS_PER_TASK}" \
    --min-bucket-coverage 2

# Copy results back to scratch
echo "[$(date)] Copying datasets back to SCRATCH..."
rsync -aq ${TMPDIR}/datasets/ ${SCRATCH}/datasets/

echo "[$(date)] Job finished!"
