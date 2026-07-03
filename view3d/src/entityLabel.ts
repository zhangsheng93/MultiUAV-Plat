import type { DroneState, ObstacleState, Position, TargetState } from './types';
import type { Locale } from './i18n.ts';
import { t, translateDataValue } from './i18n.ts';

const inFlightStatuses = new Set(['taking_off', 'flying', 'moving', 'hovering', 'landing']);

function formatPosition(position: Position, locale: Locale): string {
  const label = t(locale, 'field.position');
  const sep = locale === 'zh-CN' ? '：' : ': ';
  return `${label}${sep}x=${position.x.toFixed(1)}, y=${position.y.toFixed(1)}, z=${position.z.toFixed(1)}m`;
}

function formatNumber(value: number | undefined, fallback = '-'): string {
  return value === undefined ? fallback : String(Math.round(value));
}

export function isDroneInFlight(drone: DroneState): boolean {
  return inFlightStatuses.has(drone.status);
}

export function formatDroneInfoLines(drone: DroneState, selected: boolean, locale: Locale = 'zh-CN'): string[] {
  const speed = (drone.speed ?? 0).toFixed(1);
  const battery = formatNumber(drone.battery_level);
  const sep = locale === 'zh-CN' ? '：' : ': ';
  const statusLine = `${t(locale, 'field.name')}${sep}${drone.name} · ${t(locale, 'field.status')}${sep}${translateDataValue(locale, drone.status)}`;
  const motionLine = selected
    ? `${t(locale, 'field.battery')}${sep}${battery}% · ${t(locale, 'field.speed')}${sep}${speed}m/s · ${t(locale, 'field.heading')}${sep}${Math.round(drone.heading || 0)}°`
    : `${t(locale, 'field.battery')}${sep}${battery}% · ${t(locale, 'field.speed')}${sep}${speed}m/s`;

  return [
    statusLine,
    formatPosition(drone.position, locale),
    motionLine
  ];
}

export function formatTargetInfoLines(target: TargetState, selected: boolean, locale: Locale = 'zh-CN'): string[] {
  const sep = locale === 'zh-CN' ? '：' : ': ';
  const lines = [
    `${t(locale, 'entity.target')}${sep}${target.name} · ${t(locale, 'field.type')}${sep}${translateDataValue(locale, target.type)}`,
    formatPosition(target.position, locale)
  ];

  if (selected) {
    const radius = target.radius === undefined ? '-' : `${target.radius}m`;
    lines.push(`${t(locale, 'field.radius')}${sep}${radius} · ${t(locale, 'field.completed')}${sep}${target.is_reached ? t(locale, 'value.yes') : t(locale, 'value.no')}`);
  }

  return lines;
}

export function formatObstacleInfoLines(obstacle: ObstacleState, selected: boolean, locale: Locale = 'zh-CN'): string[] {
  const sep = locale === 'zh-CN' ? '：' : ': ';
  const lines = [
    `${t(locale, 'entity.obstacle')}${sep}${obstacle.name} · ${t(locale, 'field.type')}${sep}${translateDataValue(locale, obstacle.type)}`,
    formatPosition(obstacle.position, locale)
  ];

  if (selected) {
    const height = obstacle.height === 0 ? t(locale, 'value.notFlyable') : `${obstacle.height ?? 0}m`;
    const size = obstacle.radius !== undefined
      ? `${t(locale, 'field.radius')}${sep}${obstacle.radius}m`
      : `${t(locale, 'field.size')}${sep}${obstacle.width ?? '-'}x${obstacle.length ?? '-'}`;
    lines.push(`${t(locale, 'field.height')}${sep}${height} · ${size}`);
  }

  return lines;
}
