import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { CountryAggregate } from '../types';

interface Props {
  data: CountryAggregate[];
  topN?: number;
}

export default function CoalitionWinRateChart({ data, topN = 20 }: Props) {
  const chartData = data
    .filter((c) => c.wins > 0 && (c.solo_wins !== undefined || c.coalition_wins !== undefined))
    .sort((a, b) => b.win_rate - a.win_rate)
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      solo_pct: parseFloat((((c.solo_wins ?? 0) / c.games_played) * 100).toFixed(1)),
      coalition_pct: parseFloat((((c.coalition_wins ?? 0) / c.games_played) * 100).toFixed(1)),
      solo_wins: c.solo_wins ?? 0,
      coalition_wins: c.coalition_wins ?? 0,
    }));

  if (chartData.length === 0) return <p style={{ color: 'var(--ifm-color-emphasis-500)', fontSize: 13 }}>No coalition data available yet.</p>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 26)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 4, bottom: 8 }}
        stackOffset="none"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          width={95}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, name: string, props) => {
            const label = name === 'solo_pct' ? 'Solo wins' : 'Coalition wins';
            const count = name === 'solo_pct' ? props.payload.solo_wins : props.payload.coalition_wins;
            return [`${value}% (${count} wins)`, label];
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 11 }}
          formatter={(value) => value === 'solo_pct' ? 'Solo win %' : 'Coalition win %'}
        />
        <Bar dataKey="solo_pct" stackId="a" fill="#4a90e2" name="solo_pct" radius={[0, 0, 0, 0]} />
        <Bar dataKey="coalition_pct" stackId="a" fill="#9b59b6" name="coalition_pct" radius={[0, 3, 3, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
