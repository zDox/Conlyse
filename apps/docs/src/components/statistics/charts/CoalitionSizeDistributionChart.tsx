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

const LABELS: Record<string, string> = { '1': 'Solo', '2': '2-player', '3': '3-player', '4': '4-player', '5': '5-player' };
const COLORS: Record<string, string> = { '1': '#4a90e2', '2': '#9b59b6', '3': '#e74c3c', '4': '#f5a623', '5': '#50c878' };

export default function CoalitionSizeDistributionChart({ data }: Props) {
  const dist = data.coalition_size_distribution ?? {};
  if (Object.keys(dist).length === 0) return <p style={{ color: 'var(--ifm-color-emphasis-500)', fontSize: 13 }}>No coalition data available yet.</p>;

  const total = Object.values(dist).reduce((a, b) => a + b, 0);
  const chartData = Object.entries(dist)
    .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
    .map(([k, v]) => ({
      label: LABELS[k] ?? `${k}-player`,
      count: v,
      pct: parseFloat(((v / total) * 100).toFixed(1)),
      key: k,
    }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 4, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--ifm-font-color-base)' }} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }} />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(_: number, __: string, props) => [
            `${props.payload.pct}%`,
            'Games',
          ]}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[entry.key] ?? '#4a90e2'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
