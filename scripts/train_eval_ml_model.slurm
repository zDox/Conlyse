#!/bin/bash
#SBATCH --job-name=gnn-train-eval
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=4G
#SBATCH --time=00:30:00
#SBATCH --tmp=60g
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

# Copy datasets to node-local storage
echo "[$(date)] Copying datasets to node-local storage..."
mkdir -p ${TMPDIR}/datasets/training ${TMPDIR}/datasets/evaluation ${TMPDIR}/model ${TMPDIR}/report
rsync -aq ${SCRATCH}/datasets/training/ ${TMPDIR}/datasets/training/
rsync -aq ${SCRATCH}/datasets/evaluation/ ${TMPDIR}/datasets/evaluation/

MODEL_DIR="${TMPDIR}/model"
MODEL_PATH="${MODEL_DIR}/win_predictor.pt"
REPORT_PATH="${TMPDIR}/report/report.txt"
HTML_REPORT_PATH="${TMPDIR}/report/report.html"

# Train
echo "[$(date)] Training model..."
conlyse-predict train \
    --dataset-dir "${TMPDIR}/datasets/training" \
    --output-dir "${MODEL_DIR}" \
    --folds 5

# Evaluate and capture report
echo "[$(date)] Evaluating model..."
{
    echo "Win-predictor model report"
    echo "Generated: $(date)"
    echo "Job: ${SLURM_JOB_NAME} (${SLURM_JOB_ID})"
    echo "Training dataset: datasets/training"
    echo "Evaluation dataset: datasets/evaluation"
    echo
    conlyse-predict eval \
        --dataset-dir "${TMPDIR}/datasets/evaluation" \
        --checkpoint "${MODEL_PATH}"
} | tee "${REPORT_PATH}"

# Generate detailed HTML report (charts, calibration, progress breakdown, ...)
echo "[$(date)] Generating HTML report..."
conlyse-predict report \
    --dataset-dir "${TMPDIR}/datasets/evaluation" \
    --checkpoint "${MODEL_PATH}" \
    --output "${HTML_REPORT_PATH}"

# Copy results back to scratch
echo "[$(date)] Copying model and reports back to SCRATCH..."
mkdir -p ${SCRATCH}/models ${SCRATCH}/reports
rsync -aq "${MODEL_PATH}" "${SCRATCH}/models/win_predictor_${SLURM_JOB_ID}.pt"
rsync -aq "${REPORT_PATH}" "${SCRATCH}/reports/report_${SLURM_JOB_ID}.txt"
rsync -aq "${HTML_REPORT_PATH}" "${SCRATCH}/reports/report_${SLURM_JOB_ID}.html"

echo "[$(date)] Job finished!"
