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

const METRICS = [
  { key: 'avg_wars_per_game',          label: 'Wars Declared',   color: '#e74c3c' },
  { key: 'avg_right_of_ways_per_game', label: 'Right of Ways',   color: '#4a90e2' },
  { key: 'avg_peace_treaties_per_game',label: 'Peace Treaties',  color: '#50c878' },
  { key: 'avg_shared_intelligence_per_game', label: 'Shared Intelligence', color: '#9b59b6' },
] as const;

export default function DiplomacyGlobalChart({ data }: Props) {
  const chartData = METRICS.map((m) => ({
    name: m.label,
    value: parseFloat((data[m.key] as number).toFixed(1)),
    color: m.color,
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 48, left: 4, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          width={110}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, _: string) => [`${value} per game`, 'Avg']}
        />
        <Bar dataKey="value" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
