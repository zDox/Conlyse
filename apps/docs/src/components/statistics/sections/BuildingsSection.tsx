import React from 'react';
import BuildingFrequencyChart from '../charts/BuildingFrequencyChart';
import BuildingProgressionChart from '../charts/BuildingProgressionChart';
import CountryBuildingChart from '../charts/CountryBuildingChart';
import CountrySimilarityScatterChart from '../charts/CountrySimilarityScatterChart';
import type { BuildingAggregate, ClusterInfo, CountryAggregate, NationSimilarityAggregate, TimeSeriesOutput } from '../types';
import styles from './Section.module.css';

interface Props {
  data: BuildingAggregate[];
  countries: CountryAggregate[];
  timeseries: TimeSeriesOutput;
  similarity: NationSimilarityAggregate[];
  clusters: ClusterInfo[];
}

export default function BuildingsSection({ data, countries, timeseries, similarity, clusters }: Props) {
  if (data.length === 0) return null;

  return (
    <section id="section-buildings" className={styles.section}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.heading}>Building Analysis</h2>
          <p className={styles.description}>
            Building frequency, per-nation loadouts, and construction timelines across {data.length} building types.
          </p>
        </div>
      </div>
      <div className={styles.grid}>
        <div id="chart-buildings-frequency" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
          <h3 className={styles.chartTitle}>Building Frequency (Top 20)</h3>
          <p className={styles.chartSubtitle}>Average number of completed buildings per game across all players · sorted by frequency</p>
          <BuildingFrequencyChart data={data} />
        </div>
        <div id="chart-buildings-country" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
          <h3 className={styles.chartTitle}>Country Loadouts</h3>
          <p className={styles.chartSubtitle}>Average count at game end per nation for the selected building type · label shows avg level where available</p>
          <CountryBuildingChart countries={countries} buildings={data} />
        </div>
        <div id="chart-buildings-progression" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
          <h3 className={styles.chartTitle}>Build Progression over Game Time</h3>
          <p className={styles.chartSubtitle}>Average count of selected building type over game progress % · top 8 nations by sample size</p>
          <BuildingProgressionChart
            timeseries={timeseries.countries}
            buildings={data}
            pct_buckets={timeseries.pct_buckets}
          />
        </div>
        {similarity.length > 0 && (
          <div id="chart-buildings-similarity" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
            <h3 className={styles.chartTitle}>Nation Build Similarity</h3>
            <p className={styles.chartSubtitle}>
              Nations clustered by build composition (buildings normalized to % of that nation&apos;s builds, then PCA + k-means) ·
              restricted to nations with at least a handful of human-played games · dot color = build-style cluster
            </p>
            <CountrySimilarityScatterChart data={similarity} clusters={clusters} />
          </div>
        )}
      </div>
    </section>
  );
}
