#!/bin/bash
#SBATCH --job-name=ml-train-eval
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=4G
#SBATCH --time=00:30:00
#SBATCH --tmp=20g
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
mkdir -p ${TMPDIR}/datasets ${TMPDIR}/model ${TMPDIR}/report
rsync -aq ${SCRATCH}/datasets/training.parquet ${TMPDIR}/datasets/
rsync -aq ${SCRATCH}/datasets/evaluation.parquet ${TMPDIR}/datasets/

MODEL_PATH="${TMPDIR}/model/win_probability.lgb"
REPORT_PATH="${TMPDIR}/report/report.txt"
HTML_REPORT_PATH="${TMPDIR}/report/report.html"

# Train
echo "[$(date)] Training model..."
conlyse-predict train \
    --dataset "${TMPDIR}/datasets/training.parquet" \
    --output "${MODEL_PATH}" \
    --folds 5 \
    --min-coverage 2

# Evaluate and capture report
echo "[$(date)] Evaluating model..."
{
    echo "Win-probability model report"
    echo "Generated: $(date)"
    echo "Job: ${SLURM_JOB_NAME} (${SLURM_JOB_ID})"
    echo "Training dataset: training.parquet"
    echo "Evaluation dataset: evaluation.parquet"
    echo
    conlyse-predict eval \
        --dataset "${TMPDIR}/datasets/evaluation.parquet" \
        --model "${MODEL_PATH}" \
        --min-coverage 2
} | tee "${REPORT_PATH}"

# Generate detailed HTML report (charts, calibration, feature importance, ...)
echo "[$(date)] Generating HTML report..."
conlyse-predict report \
    --dataset "${TMPDIR}/datasets/evaluation.parquet" \
    --model "${MODEL_PATH}" \
    --output "${HTML_REPORT_PATH}" \
    --min-coverage 2

# Copy results back to scratch
echo "[$(date)] Copying model and reports back to SCRATCH..."
mkdir -p ${SCRATCH}/models ${SCRATCH}/reports
rsync -aq "${MODEL_PATH}" "${SCRATCH}/models/win_probability_${SLURM_JOB_ID}.lgb"
rsync -aq "${REPORT_PATH}" "${SCRATCH}/reports/report_${SLURM_JOB_ID}.txt"
rsync -aq "${HTML_REPORT_PATH}" "${SCRATCH}/reports/report_${SLURM_JOB_ID}.html"

echo "[$(date)] Job finished!"
