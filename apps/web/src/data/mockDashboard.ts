export type MarketSnapshot = {
  instrument: string;
  regime: 'Bullish' | 'Bearish' | 'Neutral';
  noTrade: boolean;
};

export type OpportunitySummary = {
  total: number;
  passing: number;
  review: number;
};

export type TopCandidate = {
  instrument: string;
  strike: string;
  expiry: string;
  edge: string;
  confidence: 'High' | 'Medium' | 'Low';
};

export type ModelHealth = {
  trainingDate: string;
  dataFreshness: 'Current' | 'Stale';
  status: 'Healthy' | 'Warning' | 'Degraded';
};

export type DashboardData = {
  markets: MarketSnapshot[];
  opportunities: OpportunitySummary;
  topCandidates: TopCandidate[];
  modelHealth: ModelHealth;
};

export const mockDashboard: DashboardData = {
  markets: [
    { instrument: 'EUR/USD', regime: 'Bullish', noTrade: false },
    { instrument: 'GBP/USD', regime: 'Neutral', noTrade: true },
    { instrument: 'USD/JPY', regime: 'Bearish', noTrade: false },
  ],
  opportunities: {
    total: 5,
    passing: 2,
    review: 1,
  },
  topCandidates: [
    {
      instrument: 'EUR/USD',
      strike: '1.0875',
      expiry: '2026-04-22T14:00:00Z',
      edge: '+0.14',
      confidence: 'High',
    },
    {
      instrument: 'USD/JPY',
      strike: '154.50',
      expiry: '2026-04-22T16:00:00Z',
      edge: '+0.09',
      confidence: 'Medium',
    },
  ],
  modelHealth: {
    trainingDate: '2026-04-21',
    dataFreshness: 'Current',
    status: 'Healthy',
  },
};
