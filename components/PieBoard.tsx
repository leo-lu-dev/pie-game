'use client';

import { useEffect, useRef, useState } from 'react';
import { Cell, Pie, PieChart } from 'recharts';

export const sliceColors = ['#f06d3c', '#f6b944', '#2f8994', '#7294d4', '#b57ab9'];

export function boardGeometry(width: number, values: number[]) {
  const compact = width < 720;
  const cardWidth = width < 336 ? 90 : compact ? 116 : 180;
  const cardHeight = 88;
  const clearance = compact ? 18 : 22;
  const radius = compact
    ? Math.min(210, (width - Math.max(56, cardWidth * .45)) / 2)
    : Math.min(245, (width - cardWidth * 2 - clearance * 2) / 2);
  const height = compact
    ? cardHeight * 2 + radius * 2 + clearance * 2 + 24
    : Math.max(520, radius * 2 + 96);
  const cx = width / 2;
  const cy = compact ? cardHeight + clearance + radius + 12 : height / 2;
  const total = values.reduce((sum, value) => sum + value, 0);
  let accumulated = 0;
  const cards = values.map((value, index) => {
    const angle = (90 - (accumulated + value / 2) / total * 360) * Math.PI / 180;
    accumulated += value;
    const ax = cx + radius * Math.cos(angle), ay = cy - radius * Math.sin(angle);
    const left = Math.cos(angle) < 0;
    return { index, ax, ay, left, x: 0, y: 0, path: '', elbow: 0, edge: 0, outwardDot: 0 };
  });

  if (compact) {
    const vertical = [...cards].sort((a, b) => a.ay - b.ay);
    [vertical.slice(0, 3), vertical.slice(3)].forEach((group, row) => {
      group.sort((a, b) => a.ax - b.ax).forEach((card, index) => {
        card.x = group.length === 1 ? (width - cardWidth) / 2 : index * (width - cardWidth) / (group.length - 1);
        card.y = row === 0 ? 0 : height - cardHeight;
        // Pick the card edge nearest the slice so compact-layout connectors fan
        // outward instead of crossing near the middle card.
        card.left = card.ax >= card.x + cardWidth / 2;
      });
    });
  } else {
    for (const left of [true, false]) {
      const side = cards.filter(card => card.left === left).sort((a, b) => a.ay - b.ay);
      side.forEach((card, index) => {
        card.x = left ? cx - radius - clearance - cardWidth : cx + radius + clearance;
        card.y = Math.max(8, card.ay - cardHeight / 2, index ? side[index - 1].y + cardHeight + 14 : 8);
      });
      if (side.length) {
        const overflow = Math.max(0, side[side.length - 1].y + cardHeight + 8 - height);
        side.forEach(card => { card.y -= overflow; });
      }
    }
  }

  cards.forEach(card => {
    const edge = card.left ? card.x + cardWidth : card.x;
    let elbow = edge + (card.left ? 12 : -12);
    const radialX = card.ax - cx;
    const radialY = card.ay - cy;
    const deltaY = card.y + cardHeight / 2 - card.ay;
    const minimumOutwardDot = Math.max(1, radius * .5);
    const outwardDot = (elbow - card.ax) * radialX + deltaY * radialY;
    if (outwardDot < minimumOutwardDot && Math.abs(radialX) > .001) {
      elbow += Math.sign(radialX) * (minimumOutwardDot - outwardDot) / Math.abs(radialX);
    }
    card.path = `M ${card.ax} ${card.ay} L ${elbow} ${card.y + cardHeight / 2} H ${edge}`;
    card.elbow = elbow;
    card.edge = edge;
    card.outwardDot = (elbow - card.ax) * radialX + deltaY * radialY;
  });
  return { width, height, radius, cx, cy, cardWidth, cardHeight, clearance, compact, cards };
}

type Props = {
  values: number[]; mapping: (string | null)[]; locked: boolean[]; selected: string | null;
  disabled: boolean; labelFor: (id: string | null) => string | undefined;
  onClick: (index: number) => void;
  onDragStart: (event: React.DragEvent<HTMLButtonElement>, id: string) => void;
  onDrop: (event: React.DragEvent<HTMLButtonElement>, index: number) => void;
};

export default function PieBoard(props: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  const geometry = boardGeometry(width || 1000, props.values);
  return <div ref={container} className="pie-board" style={{ height: geometry.height }}>
    {width > 0 && <>
      <PieChart width={width} height={geometry.height} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <Pie data={props.values.map(value => ({ value }))} dataKey="value" cx={geometry.cx} cy={geometry.cy}
          innerRadius={geometry.radius * .46} outerRadius={geometry.radius} startAngle={90} endAngle={-270}
          paddingAngle={0} stroke="var(--cream)" strokeWidth={3} isAnimationActive={false} labelLine={false}
          label={({ midAngle, index }) => {
            const angle = -midAngle * Math.PI / 180;
            return <text x={geometry.cx + geometry.radius * .74 * Math.cos(angle)} y={geometry.cy + geometry.radius * .74 * Math.sin(angle)} textAnchor="middle" dominantBaseline="central" fill="#17221f" fontWeight={800} fontSize={width < 720 ? 14 : 18}>{Number(index) + 1}</text>;
          }}>
          {props.values.map((_, index) => <Cell key={index} fill={sliceColors[index]} />)}
        </Pie>
      </PieChart>
      <svg className="board-connectors" width={width} height={geometry.height} aria-hidden="true">
        {geometry.cards.map(card => <path key={card.index} d={card.path} fill="none" stroke={sliceColors[card.index]} strokeWidth={2} />)}
      </svg>
      {geometry.cards.map(card => {
        const id = props.mapping[card.index], locked = props.locked[card.index];
        return <button key={card.index} className={`answer-card floating-card ${id && props.selected === id ? 'is-selected' : ''}`}
          style={{ left: card.x, top: card.y, width: geometry.cardWidth, height: geometry.cardHeight, borderColor: sliceColors[card.index], backgroundColor: locked ? '#d4f2dc' : `${sliceColors[card.index]}${id ? '55' : '20'}` }}
          disabled={props.disabled || locked} draggable={Boolean(id) && !locked && !props.disabled}
          onDragStart={event => id && props.onDragStart(event, id)} onClick={() => props.onClick(card.index)}
          onDragOver={event => { if (!locked && !props.disabled) event.preventDefault(); }} onDrop={event => props.onDrop(event, card.index)}
          aria-label={`Slice ${card.index + 1}${id ? `, ${props.labelFor(id)}` : ', empty'}`}>
          <span className="card-caption">Slice {card.index + 1}{locked ? ' · ✓ Correct' : ''}</span>
          <span>{id ? props.labelFor(id) : 'Drop here'}</span>
        </button>;
      })}
    </>}
  </div>;
}
