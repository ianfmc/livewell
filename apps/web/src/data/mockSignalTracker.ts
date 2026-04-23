export type TrackedSignal = {
  date: string;
  market: string;
  strike: string;
  expiry: string;
  recommendation: 'Take' | 'Watch' | 'Pass';
  actionTaken: 'Taken' | 'Skipped' | null;
  outcome: 'Win' | 'Loss' | 'Pending';
  edge: number;
  modelProbability: number;
};

export const mockSignals: TrackedSignal[] = [
  { date: '2026-04-23', market: 'EUR/USD', strike: '1.0880', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Pending', edge: 0.18, modelProbability: 0.70 },
  { date: '2026-04-22', market: 'GBP/USD', strike: '1.2680', expiry: '11:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Win',     edge: 0.11, modelProbability: 0.58 },
  { date: '2026-04-22', market: 'USD/JPY', strike: '154.50', expiry: '16:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Loss',    edge: -0.04, modelProbability: 0.44 },
  { date: '2026-04-21', market: 'EUR/USD', strike: '1.0860', expiry: '12:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.22, modelProbability: 0.72 },
  { date: '2026-04-21', market: 'GBP/USD', strike: '1.2650', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Loss',    edge: 0.15, modelProbability: 0.65 },
  { date: '2026-04-19', market: 'USD/JPY', strike: '154.00', expiry: '10:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Win',     edge: 0.09, modelProbability: 0.55 },
  { date: '2026-04-18', market: 'EUR/USD', strike: '1.0840', expiry: '11:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.20, modelProbability: 0.69 },
  { date: '2026-04-18', market: 'GBP/USD', strike: '1.2700', expiry: '16:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Win',     edge: -0.02, modelProbability: 0.45 },
  { date: '2026-04-17', market: 'EUR/USD', strike: '1.0870', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Loss',    edge: 0.13, modelProbability: 0.61 },
  { date: '2026-04-16', market: 'USD/JPY', strike: '153.50', expiry: '12:00', recommendation: 'Watch', actionTaken: 'Taken',   outcome: 'Win',     edge: 0.10, modelProbability: 0.57 },
  { date: '2026-04-15', market: 'EUR/USD', strike: '1.0855', expiry: '10:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.19, modelProbability: 0.68 },
  { date: '2026-04-14', market: 'GBP/USD', strike: '1.2660', expiry: '11:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Loss',    edge: -0.06, modelProbability: 0.42 },
  { date: '2026-04-12', market: 'USD/JPY', strike: '153.00', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Skipped', outcome: 'Win',     edge: 0.16, modelProbability: 0.64 },
  { date: '2026-04-11', market: 'EUR/USD', strike: '1.0830', expiry: '16:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Loss',    edge: 0.07, modelProbability: 0.53 },
  { date: '2026-04-10', market: 'GBP/USD', strike: '1.2640', expiry: '12:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.21, modelProbability: 0.71 },
];
