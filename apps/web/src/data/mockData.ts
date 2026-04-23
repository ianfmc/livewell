export type ContractCard = {
  instrument: string;
  strike: string;
  expiry: string;
  status: string;
};

export type ContractDetail = {
  instrument: string;
  strike: string;
  expiry: string;
  status: string;
  recommendation: 'Take' | 'Watch' | 'Pass';
  rationale: string;
  economics: {
    cost: number;
    payout: number;
    breakeven: number;
  };
  modelProbability: number;
  edge: number;
  confidence: 'High' | 'Medium' | 'Low';
  regime: string;
  noTradeFlag: boolean;
  reasonCodes: Array<{
    label: string;
    positive: boolean;
  }>;
};

export const mockData: ContractCard[] = [
  {
    instrument: "EUR/USD",
    strike: "1.0850",
    expiry: "10:00 AM",
    status: "Open",
  },
  {
    instrument: "GBP/USD",
    strike: "1.2650",
    expiry: "11:00 AM",
    status: "Open",
  },
  {
    instrument: "USD/JPY",
    strike: "150.00",
    expiry: "09:30 AM",
    status: "Review",
  },
];

export const mockContractDetails: ContractDetail[] = [
  {
    instrument: "EUR/USD",
    strike: "1.0850",
    expiry: "10:00 AM",
    status: "Open",
    recommendation: "Take",
    rationale: "Strong directional setup with acceptable event risk.",
    economics: { cost: 42, payout: 100, breakeven: 0.42 },
    modelProbability: 0.68,
    edge: 0.26,
    confidence: "High",
    regime: "Bullish",
    noTradeFlag: false,
    reasonCodes: [
      { label: "Bullish regime confirmed", positive: true },
      { label: "RSI momentum favourable", positive: true },
      { label: "Event risk flag active", positive: false },
    ],
  },
  {
    instrument: "GBP/USD",
    strike: "1.2650",
    expiry: "11:00 AM",
    status: "Open",
    recommendation: "Watch",
    rationale: "Setup is developing but lacks regime confirmation.",
    economics: { cost: 38, payout: 100, breakeven: 0.38 },
    modelProbability: 0.52,
    edge: 0.14,
    confidence: "Medium",
    regime: "Neutral",
    noTradeFlag: false,
    reasonCodes: [
      { label: "Price near key level", positive: true },
      { label: "Regime not confirmed", positive: false },
      { label: "Low volatility environment", positive: false },
    ],
  },
  {
    instrument: "USD/JPY",
    strike: "150.00",
    expiry: "09:30 AM",
    status: "Review",
    recommendation: "Pass",
    rationale: "No-trade flag active — intervention risk too high.",
    economics: { cost: 55, payout: 100, breakeven: 0.55 },
    modelProbability: 0.48,
    edge: -0.07,
    confidence: "Low",
    regime: "Bearish",
    noTradeFlag: true,
    reasonCodes: [
      { label: "Intervention risk elevated", positive: false },
      { label: "Bearish momentum weakening", positive: false },
      { label: "High volatility — spread risk", positive: false },
    ],
  },
];