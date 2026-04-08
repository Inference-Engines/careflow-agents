import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Brush, Legend,
} from 'recharts';
import { fetchMetricTrend } from '../lib/api';

interface Props {
  metricType: 'blood_pressure' | 'blood_glucose' | 'weight' | 'heart_rate';
}

// ── 임상 기준선 / Clinical reference thresholds ──
const BP_NORMAL = 130;    // systolic normal upper limit
const BP_ELEVATED = 140;  // systolic elevated threshold
const GLUCOSE_NORMAL = 100;
const GLUCOSE_TARGET = 140;
const WEIGHT_LOW = 50;    // kg — healthy lower bound (reference)
const WEIGHT_HIGH = 90;   // kg — overweight threshold (reference)
const HR_NORMAL = 60;     // bpm — resting lower bound
const HR_ELEVATED = 100;  // bpm — resting upper bound

const ChatTrendChart: React.FC<Props> = ({ metricType }) => {
  const [data, setData] = useState<any[]>([]);
  const [showBrush, setShowBrush] = useState(false);

  useEffect(() => {
    fetchMetricTrend(metricType, 90).then(d => {
      if (d?.length) {
        const formatted = d.map((p: any, i: number) => ({
          day: i + 1,
          date: p.recorded_at?.slice(5, 10) || p.date?.slice(5, 10) || `D${i + 1}`,
          value: metricType === 'blood_pressure'
            ? parseFloat(p.systolic || p.value?.toString().split('/')[0] || p.value || 0)
            : parseFloat(p.value || 0),
          ...(metricType === 'blood_pressure' && {
            diastolic: parseFloat(p.diastolic || p.value?.toString().split('/')[1] || 0),
          }),
        }));
        setData(formatted);
      }
    });
  }, [metricType]);

  if (!data.length) return null;

  const isBP = metricType === 'blood_pressure';
  const isWeight = metricType === 'weight';
  const isHR = metricType === 'heart_rate';
  const colorMap: Record<string, string> = {
    blood_pressure: '#1C6EF2',
    blood_glucose: '#F59E0B',
    weight: '#8B5CF6',
    heart_rate: '#EF4444',
  };
  const primaryColor = colorMap[metricType] ?? '#1C6EF2';
  const secondaryColor = '#34D399';
  const gradientId = `grad-${metricType}`;
  const labelMap: Record<string, string> = {
    blood_pressure: 'Blood Pressure Trend',
    blood_glucose: 'Blood Glucose Trend',
    weight: 'Weight Trend',
    heart_rate: 'Heart Rate Trend',
  };
  const unitMap: Record<string, string> = {
    blood_pressure: 'mmHg',
    blood_glucose: 'mg/dL',
    weight: 'kg',
    heart_rate: 'bpm',
  };
  const label = labelMap[metricType] ?? metricType;
  const unit = unitMap[metricType] ?? '';

  const avg = Math.round(data.reduce((s, d) => s + d.value, 0) / data.length);
  const min = Math.round(Math.min(...data.map(d => d.value)));
  const max = Math.round(Math.max(...data.map(d => d.value)));

  return (
    <div className="mt-3 rounded-2xl bg-surface-container-low border border-outline-variant/10 overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold text-slate-700 tracking-tight">{label}</p>
          <p className="text-[10px] text-slate-400">{data.length} readings · 90 days · AlloyDB</p>
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">Avg {avg} {unit}</span>
          <span className="text-slate-400">{min}–{max}</span>
          <button
            onClick={() => setShowBrush(b => !b)}
            className="px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 font-medium transition-colors"
          >
            {showBrush ? 'Simple' : 'Zoom'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={showBrush ? 200 : 160}>
        <AreaChart data={data} margin={{ top: 8, right: 16, left: -10, bottom: showBrush ? 30 : 4 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={primaryColor} stopOpacity={0.2} />
              <stop offset="95%" stopColor={primaryColor} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-outline-variant, #BFC4D9)" opacity={0.2} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: '#94a3b8' }}
            interval={Math.floor(data.length / 6)}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#94a3b8' }}
            domain={['auto', 'auto']}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              borderRadius: '14px',
              fontSize: '11px',
              padding: '8px 12px',
              background: 'var(--color-surface, #fff)',
              border: '1px solid var(--color-outline-variant, #e2e8f0)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            }}
            labelStyle={{ fontWeight: 700, marginBottom: 4 }}
            formatter={(val: number, name: string) => {
              const tooltipLabel: Record<string, string> = {
                blood_pressure: 'Systolic', blood_glucose: 'Glucose',
                weight: 'Weight', heart_rate: 'Heart Rate',
              };
              return [`${val} ${unit}`, name === 'diastolic' ? 'Diastolic' : tooltipLabel[metricType] ?? metricType];
            }}
          />

          {/* Reference lines — clinical thresholds */}
          {isBP && (
            <>
              <ReferenceLine y={BP_NORMAL} stroke="#059669" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Normal', fontSize: 9, fill: '#059669', position: 'right' }} />
              <ReferenceLine y={BP_ELEVATED} stroke="#DC2626" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Elevated', fontSize: 9, fill: '#DC2626', position: 'right' }} />
            </>
          )}
          {metricType === 'blood_glucose' && (
            <>
              <ReferenceLine y={GLUCOSE_NORMAL} stroke="#059669" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Normal', fontSize: 9, fill: '#059669', position: 'right' }} />
              <ReferenceLine y={GLUCOSE_TARGET} stroke="#DC2626" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Target', fontSize: 9, fill: '#DC2626', position: 'right' }} />
            </>
          )}
          {isWeight && (
            <>
              <ReferenceLine y={WEIGHT_LOW} stroke="#059669" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Low', fontSize: 9, fill: '#059669', position: 'right' }} />
              <ReferenceLine y={WEIGHT_HIGH} stroke="#DC2626" strokeDasharray="4 4" opacity={0.6} label={{ value: 'High', fontSize: 9, fill: '#DC2626', position: 'right' }} />
            </>
          )}
          {isHR && (
            <>
              <ReferenceLine y={HR_NORMAL} stroke="#059669" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Normal', fontSize: 9, fill: '#059669', position: 'right' }} />
              <ReferenceLine y={HR_ELEVATED} stroke="#DC2626" strokeDasharray="4 4" opacity={0.6} label={{ value: 'Elevated', fontSize: 9, fill: '#DC2626', position: 'right' }} />
            </>
          )}

          {/* Main line + gradient fill */}
          <Area
            type="monotone"
            dataKey="value"
            stroke={primaryColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, stroke: primaryColor, strokeWidth: 2, fill: '#fff' }}
            animationDuration={1200}
            animationEasing="ease-out"
          />

          {/* Diastolic line for BP */}
          {isBP && (
            <Area
              type="monotone"
              dataKey="diastolic"
              stroke={secondaryColor}
              strokeWidth={1.5}
              fill="none"
              dot={false}
              activeDot={{ r: 3, stroke: secondaryColor, strokeWidth: 2, fill: '#fff' }}
              animationDuration={1200}
            />
          )}

          {isBP && <Legend verticalAlign="top" height={20} iconType="line" wrapperStyle={{ fontSize: 10 }} />}

          {/* Brush for zoom/pan */}
          {showBrush && (
            <Brush dataKey="date" height={20} stroke={primaryColor} travellerWidth={8} />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ChatTrendChart;
