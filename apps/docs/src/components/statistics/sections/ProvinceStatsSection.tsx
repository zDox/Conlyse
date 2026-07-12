import React, { useState } from 'react';
import ProvinceStrategicScatterChart from '../charts/ProvinceStrategicScatterChart';
import type { ProvinceAggregate } from '../types';
import styles from './Section.module.css';

interface Props {
  data: ProvinceAggregate[];
}

export default function ProvinceStatsSection({ data }: Props) {
  const [showCoastal, setShowCoastal] = useState<'all' | 'land' | 'coastal'>('all');

  const urban = data.filter((p) => p.terrain_type === 'URBAN');

  const filtered = urban.filter((p) => {
    if (showCoastal === 'coastal') return p.is_coastal;
    if (showCoastal === 'land') return !p.is_coastal;
    return true;
  });

  return (
    <section id="section-provinces" className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.heading}>Province Analysis</h2>
          <p className={styles.description}>
            Strategic importance and contest patterns across {urban.length} urban provinces.
          </p>
        </div>
        <div className={styles.filter}>
          <label className={styles.filterLabel}>Filter:</label>
          <select
            className={styles.filterSelect}
            value={showCoastal}
            onChange={(e) => setShowCoastal(e.target.value as 'all' | 'land' | 'coastal')}
          >
            <option value="all">All cities</option>
            <option value="land">Inland only</option>
            <option value="coastal">Coastal only</option>
          </select>
        </div>
      </div>
      <div className={styles.grid}>
        <div id="chart-provinces-strategic" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
          <h3 className={styles.chartTitle}>Province Strategic Map</h3>
          <p className={styles.chartSubtitle}>Urban provinces · avg ownership changes per game vs winner control rate · reference lines at medians · top outliers labeled · coloured by region</p>
          <ProvinceStrategicScatterChart data={filtered} />
        </div>
      </div>
    </section>
  );
}
