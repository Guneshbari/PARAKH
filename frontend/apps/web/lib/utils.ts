import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatScore(score: number, max = 850): string {
  return `${score} / ${max}`;
}

export function getRiskLabel(risk: string): string {
  switch (risk) {
    case 'LOWER_ESTIMATED RISK':
    case 'LOWER':
      return 'LOWER ESTIMATED RISK';
    case 'MODERATE_ESTIMATED RISK':
    case 'MODERATE':
      return 'MODERATE ESTIMATED RISK';
    case 'HIGHER_ESTIMATED RISK':
    case 'HIGHER':
      return 'HIGHER ESTIMATED RISK';
    default:
      return 'INSUFFICIENT EVIDENCE / MANUAL REVIEW';
  }
}
