export type FeatureStatus = {
  name: string;
  status: 'Available' | 'Stale' | 'Missing';
};

export type DriftWarning = {
  feature: string;
  description: string;
};

export type ModelHealth = {
  overallStatus: 'Healthy' | 'Warning' | 'Degraded';
  trainingDate: string;
  dataFreshness: string;
  calibrationError: number;
  validationAccuracy: number;
  features: FeatureStatus[];
  driftWarnings: DriftWarning[];
};

export const mockModelHealth: ModelHealth = {
  overallStatus: 'Warning',
  trainingDate: '2026-04-18',
  dataFreshness: '5 days ago',
  calibrationError: 0.043,
  validationAccuracy: 0.64,
  features: [
    { name: 'EMA-20',         status: 'Available' },
    { name: 'EMA-50',         status: 'Available' },
    { name: 'RSI-14',         status: 'Available' },
    { name: 'MACD Signal',    status: 'Available' },
    { name: 'ATR-14',         status: 'Available' },
    { name: 'Session Flag',   status: 'Available' },
    { name: 'Volatility Reg', status: 'Stale' },
    { name: 'Event Risk Flag', status: 'Missing' },
  ],
  driftWarnings: [
    {
      feature: 'Volatility Reg',
      description: 'Last computed 6 days ago — refresh recommended before next scoring run.',
    },
  ],
};
