'use client';

import { useEffect, useRef, useState } from 'react';
import { Cell, Pie, PieChart } from 'recharts';

export const sliceColors = ['#f06d3c', '#f6b944', '#2f8994', '#7294d4', '#b57ab9'];

export function boardGeometry(width: number, values: number[], radiusLimit = 140) {
  const compact = width < 720;
  const cardWidth = compact ? Math.min(132, (width - 16) / 3) : 180;
  const cardHeight = compact ? 60 : 88;
  const clearance = compact ? 10 : 22;
  const radius = compact
    ? Math.min(radiusLimit, (width - 32) / 2)
    : Math.min(245, (width - cardWidth * 2 - clearance * 2) / 2);
  let height = compact
    ? cardHeight * 2 + radius * 2 + clearance * 2 + 24
    : Math.max(520, radius * 2 + 96);
  const cx = width / 2;
  let cy = compact ? cardHeight + clearance + radius + 12 : height / 2;
  const total = values.reduce((sum, value) => sum + value, 0);
  let accumulated = 0;
  const cards = values.map((value, index) => {
    const angle = (90 - (accumulated + value / 2) / total * 360) * Math.PI / 180;
    accumulated += value;
    const ax = cx + radius * Math.cos(angle), ay = cy - radius * Math.sin(angle);
    const left = Math.cos(angle) < 0;
    return { index, ax, ay, left, x: 0, y: 0, path: '', points: [] as [number, number][], outwardDot: 0 };
  });

  if (compact) {
    const vertical = [...cards].sort((a, b) => a.ay - b.ay);
    const rows = [vertical.slice(0, 3), vertical.slice(3)];
    rows.forEach((group, row) => {
      group.sort((a, b) => a.ax - b.ax).forEach((card, index) => {
        card.x = group.length === 1 ? (width - cardWidth) / 2 : index * (width - cardWidth) / (group.length - 1);
        // A small stagger separates the leads without reserving a full card row.
        card.y = row === 0 ? (group.length === 3 && index === 1 ? -20 : 0) : height - cardHeight;
        // Pick the card edge nearest the slice so compact-layout connectors fan
        // outward instead of crossing near the middle card.
        card.left = card.ax >= card.x + cardWidth / 2;
        const elbow = card.left ? card.x + cardWidth + 12 : card.x - 12;
        const rx = card.ax - cx, ry = card.ay - cy;
        if ((elbow - card.ax) * rx + (card.y + cardHeight / 2 - card.ay) * ry <= 0 && Math.abs(ry) > .001) {
          card.y = card.ay + (radius - (elbow - card.ax) * rx) / ry - cardHeight / 2;
        }
        card.y = row === 0
          ? Math.min(card.y, cy - radius - clearance - cardHeight)
          : Math.max(card.y, cy + radius + clearance);
      });
    });
    const [topRow, bottomRow] = rows;
    bottomRow.forEach(card => {
      const sameColumn = topRow.filter(other => Math.abs(other.x - card.x) < 1);
      if (sameColumn.length) card.y = Math.max(card.y, ...sameColumn.map(other => other.y + cardHeight + 6));
    });
  } else {
    for (const left of [true, false]) {
      const side = cards.filter(card => card.left === left).sort((a, b) => a.ay - b.ay);
      side.forEach((card, index) => {
        card.x = left ? cx - radius - clearance - cardWidth : cx + radius + clearance;
        card.y = Math.max(8, card.ay - cardHeight / 2, index ? side[index - 1].y + cardHeight + 14 : 8);
      });
      // Pack the upper cards upward, not down into the tangents of smaller slices.
      for (let index = side.length - 1; index >= 0; index--) {
        const card = side[index];
        const rx = card.ax - cx, ry = card.ay - cy;
        const elbow = left ? card.x + cardWidth + 12 : card.x - 12;
        if (ry < 0) {
          const limit = card.ay + (radius - (elbow - card.ax) * rx) / ry - cardHeight / 2;
          card.y = Math.min(card.y, limit, index + 1 < side.length ? side[index + 1].y - cardHeight - 14 : Infinity);
        }
      }
      side.forEach((card, index) => {
        const rx = card.ax - cx, ry = card.ay - cy;
        const elbow = left ? card.x + cardWidth + 12 : card.x - 12;
        if (ry > 0) {
          const limit = card.ay + (radius - (elbow - card.ax) * rx) / ry - cardHeight / 2;
          card.y = Math.max(card.y, limit, index ? side[index - 1].y + cardHeight + 14 : -Infinity);
        }
      });
    }
  }

  const shift = Math.max(0, 8 - Math.min(...cards.map(card => card.y)));
  cy += shift;
  cards.forEach(card => { card.y += shift; card.ay += shift; });
  height = Math.max(height + shift, ...cards.map(card => card.y + cardHeight + 8));

  cards.forEach(card => {
    const radialX = card.ax - cx;
    const radialY = card.ay - cy;
    const edges = [
      { x: card.x, y: card.y + cardHeight / 2, nx: -1, ny: 0 },
      { x: card.x + cardWidth, y: card.y + cardHeight / 2, nx: 1, ny: 0 },
      { x: card.x + cardWidth / 2, y: card.y, nx: 0, ny: -1 },
      { x: card.x + cardWidth / 2, y: card.y + cardHeight, nx: 0, ny: 1 },
    ];
    const edge = edges.sort((a, b) => Math.hypot(a.x - card.ax, a.y - card.ay) - Math.hypot(b.x - card.ax, b.y - card.ay))[0];
    // Overlap the 3px chart stroke so the connector reaches the colored rim.
    card.points = [
      [card.ax - radialX / radius * 2, card.ay - radialY / radius * 2],
      [card.ax + radialX / radius * 10, card.ay + radialY / radius * 10],
      [edge.x + edge.nx * 10, edge.y + edge.ny * 10],
      [edge.x, edge.y],
    ];
    card.path = card.points.map(([x, y], index) => `${index ? 'L' : 'M'} ${x} ${y}`).join(' ');
    card.outwardDot = (card.points[1][0] - card.ax) * radialX + (card.points[1][1] - card.ay) * radialY;
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
  const [availableHeight, setAvailableHeight] = useState(0);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setWidth(entry.contentRect.width);
      setAvailableHeight(entry.contentRect.height);
    });
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  let geometry = boardGeometry(width || 1000, props.values);
  // Preserve label dimensions while spending the remaining vertical space on the pie.
  if (geometry.compact && availableHeight > 0) {
    for (let radius = geometry.radius - 2; geometry.height > availableHeight && radius >= 48; radius -= 2) {
      geometry = boardGeometry(width, props.values, radius);
    }
  }
  return <div ref={container} className="pie-board" style={{ height: geometry.height }}>
    {width > 0 && <>
      <PieChart width={width} height={geometry.height} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
        <Pie data={props.values.map(value => ({ value }))} dataKey="value" cx={geometry.cx} cy={geometry.cy}
          innerRadius={geometry.radius * .46} outerRadius={geometry.radius} startAngle={90} endAngle={-270}
          paddingAngle={0} stroke="var(--cream)" strokeWidth={3} isAnimationActive={false}>
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
          <span>{id ? props.labelFor(id) : 'Drop here'}</span>
        </button>;
      })}
    </>}
  </div>;
}
