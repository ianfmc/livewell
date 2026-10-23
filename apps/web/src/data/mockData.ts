export type ReasonCode = {
  label: string;
  positive: boolean;
};

export type SupportingSignals = {
  ema20: number | null;
  ema50: number | null;
  rsi14: number | null;
  macdHist: number | null;
  atr14: number | null;
};

export type ContractCard = {
  instrument: string;
  signalId: string;
  strike: string;
  expiry: string;
  status: string;
  // LW-207: candidate now carries direction, timestamp, supporting signals,
  // reason codes, and confidence/uncertainty context.
  direction: string;
  date: string;
  recommendation: "Take" | "Watch" | "Pass";
  confidence: "High" | "Medium" | "Low";
  scoreAvailable: boolean;
  edge: number;
  supportingSignals: SupportingSignals;
  reasonCodes: ReasonCode[];
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
    signalId: "EURUSD__2026-05-04",
    strike: "1.0850",
    expiry: "10:00 AM",
    status: "Open",
    direction: "buy",
    date: "2026-05-04",
    recommendation: "Take",
    confidence: "High",
    scoreAvailable: true,
    edge: 0.42,
    supportingSignals: { ema20: 1.085, ema50: 1.08, rsi14: 58, macdHist: 0.0002, atr14: 0.005 },
    reasonCodes: [{ label: "All stages passed", positive: true }],
  },
  {
    instrument: "GBP/USD",
    signalId: "GBPUSD__2026-05-04",
    strike: "1.2650",
    expiry: "11:00 AM",
    status: "Open",
    direction: "sell",
    date: "2026-05-04",
    recommendation: "Take",
    confidence: "Medium",
    scoreAvailable: true,
    edge: 0.18,
    supportingSignals: { ema20: 1.262, ema50: 1.268, rsi14: 41, macdHist: -0.0003, atr14: 0.006 },
    reasonCodes: [{ label: "All stages passed", positive: true }],
  },
  {
    instrument: "USD/JPY",
    signalId: "USDJPY__2026-05-04",
    strike: "150.00",
    expiry: "09:30 AM",
    status: "Review",
    direction: "none",
    date: "2026-05-04",
    recommendation: "Watch",
    confidence: "Low",
    scoreAvailable: false,
    edge: 0.0,
    supportingSignals: { ema20: 149.9, ema50: 149.95, rsi14: 52, macdHist: 0.0, atr14: 0.4 },
    reasonCodes: [{ label: "Momentum — bullish conditions not met", positive: false }],
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