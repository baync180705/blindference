import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface RiskGaugeProps {
  score: number;
  size?: number;
}

export function RiskGauge({ score, size = 200 }: RiskGaugeProps) {
  const data = [
    { name: 'score', value: score },
    { name: 'remaining', value: 100 - score },
  ];
  
  const getColor = (s: number) => {
    if (s <= 45) return '#10b981'; // green
    if (s < 70) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };
  
  const color = getColor(score);
  
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            startAngle={180}
            endAngle={0}
            innerRadius={size * 0.3}
            outerRadius={size * 0.4}
            paddingAngle={0}
            dataKey="value"
            isAnimationActive={true}
          >
            <Cell fill={color} />
            <Cell fill="rgba(255,255,255,0.05)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold font-mono tracking-tighter" style={{ color }}>{score}</span>
        <span className="text-xs text-gray-400 font-medium tracking-wider uppercase mt-1">Risk Score</span>
      </div>
    </div>
  );
}
