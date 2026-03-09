#!/bin/bash
#SBATCH --job-name=recording_conversion
#SBATCH --time=01:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem-per-cpu=3G
#SBATCH --output=recording_conversion_%j.out
#SBATCH --error=recording_conversion_%j.err
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
  --processes $SLURM_CPUS_PER_TASK \
  --overwrite \
  -q


echo "[$(date)] Loading modules for compression..."
module load stack/2025-06
module load pigz/2.8

echo "[$(date)] Compressing replays_out directory..."
tar cf - replays_out | pigz -p $SLURM_CPUS_PER_TASK > replays_out.tar.gz


# Copy results back
echo "[$(date)] Copying results back to SCRATCH..."

rsync -aq --delete ${TMPDIR}/replays_out/ ${SCRATCH}/replays_out/
rsync -aq ${TMPDIR}/replays_out.tar.gz ${SCRATCH}/replays_out.tar.gz

echo "[$(date)] Job finished!"