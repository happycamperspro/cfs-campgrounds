import { US_STATES, SOURCE_LABELS } from './constants';

export function formatPrice(min, max) {
  if (!min && !max) return 'Free / Unknown';
  if (min && max && min !== max) return `$${min} – $${max}`;
  return `$${min || max}`;
}

export function formatRating(average, count) {
  if (!average || average === 0) return null;
  const stars = average.toFixed(1);
  const reviews = count ? `(${count})` : '';
  return `${stars} ${reviews}`.trim();
}

export function getStateName(code) {
  return US_STATES[code] || code;
}

export function getSourceLabel(source) {
  return SOURCE_LABELS[source] || source;
}

export function truncate(str, maxLen = 150) {
  if (!str || str.length <= maxLen) return str;
  return str.slice(0, maxLen).replace(/\s+\S*$/, '') + '...';
}

export function pluralize(count, singular, plural) {
  return count === 1 ? `${count} ${singular}` : `${count} ${plural || singular + 's'}`;
}

export function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}
