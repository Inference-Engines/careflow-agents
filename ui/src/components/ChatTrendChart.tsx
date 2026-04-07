import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { fetchMetricTrend } from '../lib/api';

interface Props {
  metricType: 'blood_pressure' | 'blood_glucose';
}

const ChatTrendChart: React.FC<Props> = ({ metricType }) => {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetchMetricTrend(metricType, 90).then(d => {
      if (d?.length) {
        // Format for recharts - take every 3rd point for cleaner chart
        const formatted = d.filter((_: any, i: number) => i % 3 === 0).map((p: any) => ({
          date: p.recorded_at?.slice(5, 10) || `D${p.day}`,
          value: metricType === 'blood_pressure'
            ? parseFloat(p.systolic || p.value?.toString().split('/')[0] || p.value || 0)
            : parseFloat(p.value || 0),
        }));
        setData(formatted);
      }
    });
  }, [metricType]);

  if (!data.length) return null;

  const color = metricType === 'blood_pressure' ? '#1C6EF2' : '#F59E0B';
  const label = metricType === 'blood_pressure' ? 'Blood Pressure (mmHg)' : 'Blood Glucose (mg/dL)';

  return (
    <div className="mt-3 p-3 rounded-2xl bg-surface-container-low border border-outline-variant/10">
      <p className="text-xs font-semibold text-slate-500 mb-2">{label} — 90 Day Trend</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant, #BFC4D9)" opacity={0.3} />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" />
          <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" domain={['auto', 'auto']} />
          <Tooltip contentStyle={{ borderRadius: '12px', fontSize: '12px' }} />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ChatTrendChart;
