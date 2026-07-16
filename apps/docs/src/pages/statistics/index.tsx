import Layout from '@theme/Layout';
import React, { useEffect, useState } from 'react';
import StatsSidebar from '../../components/statistics/StatsSidebar';
import StatsHero from '../../components/statistics/StatsHero';
import BuildingsSection from '../../components/statistics/sections/BuildingsSection';
import CountryStatsSection from '../../components/statistics/sections/CountryStatsSection';
import EconomicStatsSection from '../../components/statistics/sections/EconomicStatsSection';
import GlobalStatsSection from '../../components/statistics/sections/GlobalStatsSection';
import ProvinceStatsSection from '../../components/statistics/sections/ProvinceStatsSection';
import {
  deserializeBuildings,
  deserializeCountries,
  deserializeNationSimilarity,
  deserializeProvinces,
  deserializeTimeSeries,
} from '../../components/statistics/deserialize';
import type {
  BuildingAggregate,
  ClusterInfo,
  CountryAggregate,
  GlobalAggregate,
  MetaInfo,
  NationSimilarityAggregate,
  ProvinceAggregate,
  TimeSeriesOutput,
} from '../../components/statistics/types';
import styles from './statistics.module.css';

interface StatsData {
  global: GlobalAggregate;
  countries: CountryAggregate[];
  provinces: ProvinceAggregate[];
  meta: MetaInfo;
  timeseries: TimeSeriesOutput;
  buildings: BuildingAggregate[];
  nationSimilarity: NationSimilarityAggregate[];
  buildClusters: ClusterInfo[];
}

const STATS_BASE_URL = process.env.NODE_ENV === 'development'
  ? '/data/stats'
  : 'https://r2.conlyse.zdox.dev/stats';

async function fetchStats(): Promise<StatsData> {
  const [global, countriesRaw, provincesRaw, meta, timeseriesRaw, buildingsRaw, nationSimilarityRaw] = await Promise.all([
    fetch(`${STATS_BASE_URL}/global.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/countries.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/provinces.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/meta.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/timeseries.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/buildings.json`).then((r) => r.json()),
    fetch(`${STATS_BASE_URL}/nation_similarity.json`).then((r) => r.json()),
  ]);
  const { nations: nationSimilarity, clusters: buildClusters } = deserializeNationSimilarity(nationSimilarityRaw);
  return {
    global,
    countries: deserializeCountries(countriesRaw),
    provinces: deserializeProvinces(provincesRaw),
    meta,
    timeseries: deserializeTimeSeries(timeseriesRaw),
    buildings: deserializeBuildings(buildingsRaw),
    nationSimilarity,
    buildClusters,
  };
}

export default function StatisticsPage() {
  const [data, setData] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats()
      .then(setData)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <Layout
      title="Statistics"
      description="Aggregated statistics from 1000+ recorded Conflict of Nations games"
    >
      <div className={styles.pageLayout}>
        {data && <StatsSidebar />}
        <main className={styles.main}>
          {error && (
            <div className={styles.error}>
              <strong>Could not load statistics.</strong> Run the extractor first:
              <pre className={styles.errorPre}>
                {`pip install -e tools/game_stats_extractor\ngame-stats-extractor --replays-dir /path/to/replays --output /tmp/stats\n# then upload /tmp/stats/*.json to ${STATS_BASE_URL}`}
              </pre>
              <p className={styles.errorDetail}>{error}</p>
            </div>
          )}

          {!data && !error && (
            <div className={styles.loading}>
              <div className={styles.spinner} />
              <p>Loading statistics…</p>
            </div>
          )}

          {data && (
            <>
              <StatsHero global={data.global} meta={data.meta} countries={data.countries} />
              <GlobalStatsSection data={data.global} timeseries={data.timeseries} />
              <CountryStatsSection data={data.countries} timeseries={data.timeseries} />
              <EconomicStatsSection global={data.global} countries={data.countries} timeseries={data.timeseries} />
              <ProvinceStatsSection data={data.provinces} />
              <BuildingsSection
                data={data.buildings}
                countries={data.countries}
                timeseries={data.timeseries}
                similarity={data.nationSimilarity}
                clusters={data.buildClusters}
              />
            </>
          )}
        </main>
      </div>
    </Layout>
  );
}
