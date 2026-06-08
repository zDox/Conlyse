import React from 'react';
import CoalitionSizeDistributionChart from '../charts/CoalitionSizeDistributionChart';
import DiplomacyGlobalChart from '../charts/DiplomacyGlobalChart';
import EliminationTimingDistributionChart from '../charts/EliminationTimingDistributionChart';
import GameDurationChart from '../charts/GameDurationChart';
import PlayerActivityTimeSeriesChart from '../charts/PlayerActivityTimeSeriesChart';
import PlayerDropoutChart from '../charts/PlayerDropoutChart';
import TopCoalitionPairsChart from '../charts/TopCoalitionPairsChart';
import VictoryTypeChart from '../charts/VictoryTypeChart';
import type { GlobalAggregate, TimeSeriesOutput } from '../types';
import styles from './Section.module.css';

interface Props {
  data: GlobalAggregate;
  timeseries: TimeSeriesOutput;
}

export default function GlobalStatsSection({ data, timeseries }: Props) {
  return (
    <section id="section-global" className={styles.section}>
      <h2 className={styles.heading}>Global Overview</h2>
      <p className={styles.description}>
        Patterns across all {data.total_games.toLocaleString()} recorded games.
      </p>
      <div className={styles.grid}>
        <div id="chart-global-duration" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Game Duration Distribution</h3>
          <p className={styles.chartSubtitle}>
            Mean {(data.avg_duration_hours / 24).toFixed(0)}d · Median {(data.median_duration_hours / 24).toFixed(0)}d · σ {(data.std_duration_hours / 24).toFixed(0)}d
          </p>
          <GameDurationChart
            data={data.duration_distribution}
            mean_days={data.avg_duration_hours / 24}
            median_days={data.median_duration_hours / 24}
          />
        </div>
        <div id="chart-global-victory" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Victory Types</h3>
          <p className={styles.chartSubtitle}>How games were won</p>
          <VictoryTypeChart data={data.victory_type_distribution} />
        </div>
        <div id="chart-global-dropout" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Player Dropout</h3>
          <p className={styles.chartSubtitle}>
            Avg {(data.avg_dropout_rate * 100).toFixed(0)}% of players drop out before the game ends
          </p>
          <PlayerDropoutChart dropout_rate={data.avg_dropout_rate} total_players={data.avg_players_per_game} />
        </div>
        <div id="chart-global-diplomacy" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Diplomacy per Game</h3>
          <p className={styles.chartSubtitle}>
            Avg {data.avg_wars_per_game.toFixed(0)} wars · {data.avg_right_of_ways_per_game.toFixed(0)} right-of-ways · {data.avg_peace_treaties_per_game.toFixed(0)} peace treaties · {data.avg_shared_intelligence_per_game.toFixed(0)} shared intel
          </p>
          <DiplomacyGlobalChart data={data} />
        </div>
        <div id="chart-global-activity" className={styles.chartCard} style={{ gridColumn: '1 / -1' }}>
          <h3 className={styles.chartTitle}>Player Activity Over Time</h3>
          <p className={styles.chartSubtitle}>Avg alive players and active humans at each point in a typical game · use buttons to switch time axis</p>
          <PlayerActivityTimeSeriesChart data={timeseries} />
        </div>
        <div id="chart-global-coalition-size" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Coalition Size Distribution</h3>
          <p className={styles.chartSubtitle}>How many players shared the win — solo vs 2-, 3-, or more-player coalitions</p>
          <CoalitionSizeDistributionChart data={data} />
        </div>
        <div id="chart-global-coalition-pairs" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Most Common Coalition Partners (Top 15)</h3>
          <p className={styles.chartSubtitle}>Nation pairs that won the most games together as coalition partners</p>
          <TopCoalitionPairsChart data={data} topN={15} />
        </div>
        <div id="chart-global-elim-timing" className={styles.chartCard}>
          <h3 className={styles.chartTitle}>When Do Players Get Eliminated?</h3>
          <p className={styles.chartSubtitle}>Distribution of elimination events by game progress (human players only)</p>
          <EliminationTimingDistributionChart data={data} />
        </div>
      </div>
    </section>
  );
}
