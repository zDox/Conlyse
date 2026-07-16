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

export default function CountryMoraleChart({ data, topN = 20 }: Props) {
  const chartData = data
    .filter((c) => (c.avg_national_morale ?? 0) > 0)
    .sort((a, b) => (b.avg_national_morale ?? 0) - (a.avg_national_morale ?? 0))
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      morale: parseFloat((c.avg_national_morale ?? 0).toFixed(1)),
      win_rate: parseFloat((c.win_rate * 100).toFixed(1)),
    }));

  if (chartData.length === 0) return <p style={{ color: 'var(--ifm-color-emphasis-500)', fontSize: 13 }}>No morale data available yet.</p>;

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
            `${value}% morale · ${props.payload.win_rate}% win rate`,
            'Avg national morale',
          ]}
        />
        <Bar dataKey="morale" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.morale >= 70 ? '#50c878' : entry.morale >= 55 ? '#f5a623' : '#e74c3c'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
