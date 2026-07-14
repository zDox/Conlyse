import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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

export default function CountryEliminationTimingChart({ data, topN = 20 }: Props) {
  const chartData = data
    .filter((c) => c.avg_elimination_pct != null && c.elimination_rate > 0.1)
    .sort((a, b) => (a.avg_elimination_pct ?? 100) - (b.avg_elimination_pct ?? 100))
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      avg_elim_pct: parseFloat((c.avg_elimination_pct ?? 0).toFixed(1)),
      elim_rate: parseFloat((c.elimination_rate * 100).toFixed(1)),
    }));

  if (chartData.length === 0) return <p style={{ color: 'var(--ifm-color-emphasis-500)', fontSize: 13 }}>No elimination timing data available yet.</p>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 26)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 4, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 100]}
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
          formatter={(value: number, _: string, props) => [
            `Eliminated at ${value}% of game · ${props.payload.elim_rate}% elim rate`,
            'Avg elimination point',
          ]}
        />
        <Bar dataKey="avg_elim_pct" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.avg_elim_pct < 33 ? '#e74c3c' : entry.avg_elim_pct < 60 ? '#f5a623' : '#50c878'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
