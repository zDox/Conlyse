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
import type { GlobalAggregate } from '../types';

interface Props {
  data: GlobalAggregate;
}

export default function EliminationTimingDistributionChart({ data }: Props) {
  const dist = data.elimination_timing_distribution ?? {};
  if (Object.keys(dist).length === 0) return <p style={{ color: 'var(--ifm-color-emphasis-500)', fontSize: 13 }}>No elimination timing data available yet.</p>;

  const total = Object.values(dist).reduce((s, v) => s + v, 0);

  const chartData = Object.keys(dist)
    .map((b) => parseInt(b))
    .sort((a, b) => a - b)
    .map((bucket) => ({
      label: `Day ${bucket}–${bucket + 10}`,
      bucket,
      pct: total > 0 ? ((dist[String(bucket)] ?? 0) / total) * 100 : 0,
    }))
    .filter((d) => d.pct > 0);

  const max = Math.max(...chartData.map((d) => d.pct));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 4, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: 'var(--ifm-font-color-base)' }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }} />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number) => [`${value.toFixed(1)}%`, 'Eliminations']}
        />
        <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.pct === max ? '#e74c3c' : '#4a90e2'}
              fillOpacity={0.85 + (entry.pct / max) * 0.15}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
