#!/bin/bash
#SBATCH --job-name=recording_conversion
#SBATCH --time=00:5:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=3G
#SBATCH --output=first_job_%j.out
#SBATCH --error=first_job_%j.err
#SBATCH --tmp=100g

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

# Copy Data to TMP
echo "[$(date)] Copying data to node-local storage..."
rsync -aq ${SCRATCH}/converted_recordings.zip ${TMPDIR}/

cd $TMPDIR
echo "[$(date)] Unzipping archive..."
unzip -q converted_recordings.zip
rm converted_recordings.zip

# Run conversion
echo "[$(date)] Running recording conversion..."
recording-converter \
  --recording-dir converted_recordings \
  --output-dir replays_out \
  --mode rur \
  --bulk \
  --processes 1 \
  --recording-name game_10637077 \
  -q

# Copy results back
echo "[$(date)] Copying results back to SCRATCH..."
rsync -auq ${TMPDIR}/replays_out/ ${SCRATCH}/replays_out/

echo "[$(date)] Job finished!"