import React from 'react';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface Props {
  data: Record<string, number>;
  totalTraitorWins?: number;
}

const SLICE_META: Record<string, { label: string; color: string }> = {
  solo: { label: 'Solo Victory (Loyal)', color: '#4a90e2' },
  solo_traitor: { label: 'Solo Victory (Traitor)', color: '#e74c3c' },
  coalition: { label: 'Coalition Victory', color: '#50c878' },
  unknown: { label: 'Unknown', color: '#f5a623' },
};

export default function VictoryTypeChart({ data, totalTraitorWins }: Props) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .flatMap(([key, value]) => {
      if (key === 'solo' && totalTraitorWins) {
        const traitor = Math.min(totalTraitorWins, value);
        const loyal = value - traitor;
        return [
          loyal > 0 ? { key: 'solo', value: loyal } : null,
          traitor > 0 ? { key: 'solo_traitor', value: traitor } : null,
        ].filter((d): d is { key: string; value: number } => d !== null);
      }
      return [{ key, value }];
    })
    .map(({ key, value }) => ({
      key,
      name: SLICE_META[key]?.label ?? key,
      value,
      color: SLICE_META[key]?.color ?? '#999999',
    }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          dataKey="value"
        >
          {chartData.map((d) => (
            <Cell key={`cell-${d.key}`} fill={d.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, name: string) => {
            const total = chartData.reduce((s, d) => s + d.value, 0);
            return [`${((value / total) * 100).toFixed(1)}%`, name];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: 'var(--ifm-font-color-base)' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
