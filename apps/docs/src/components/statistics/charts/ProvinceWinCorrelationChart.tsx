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
import type { ProvinceAggregate } from '../types';

interface Props {
  data: ProvinceAggregate[];
  topN?: number;
}

export default function ProvinceWinCorrelationChart({ data, topN = 25 }: Props) {
  const chartData = [...data]
    .sort((a, b) => b.win_correlation - a.win_correlation)
    .slice(0, topN)
    .map((p) => ({
      name: p.province_name,
      win_pct: parseFloat((p.win_correlation * 100).toFixed(1)),
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 24)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 110, bottom: 8 }}
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
          tick={{ fontSize: 10, fill: 'var(--ifm-font-color-base)' }}
          width={105}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number) => [`${value}%`, 'Winner controlled']}
        />
        <Bar dataKey="win_pct" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.win_pct >= 75 ? '#50c878' : entry.win_pct >= 50 ? '#4a90e2' : '#f5a623'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
