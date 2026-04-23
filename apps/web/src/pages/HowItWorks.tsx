import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const SECTIONS = [
  {
    title: 'What LIVEWELL Predicts',
    content: `LIVEWELL predicts whether a NADEX binary contract will expire in the money. Each contract has a fixed payout (usually $100) and a cost set by the market. The model estimates the probability that the underlying price will be above or below the contract's strike at expiry. A model probability of 0.68 means the model believes there is a 68% chance the contract expires in the money. The breakeven probability is the cost divided by the payout — if you pay $42 for a $100 contract, breakeven is 42%. Edge is the difference: 68% − 42% = 26%.`,
    example: 'Example: EUR/USD > 1.0850 by 14:00. Cost $42. Payout $100. Breakeven 42%. Model probability 68%. Estimated edge +26%.',
  },
  {
    title: 'How Edge Is Calculated',
    content: `Edge is payout-aware expected value. It is not raw model accuracy. A model with 60% accuracy on a 50% breakeven contract has edge. The same model on a 65% breakeven contract does not. The formula is: Edge = Model Probability − Breakeven Probability. Positive edge means the model believes the contract is underpriced by the market. LIVEWELL only recommends contracts where edge clears a minimum threshold after accounting for transaction costs.`,
    example: 'Example: Model probability 0.62. Contract cost $55. Payout $100. Breakeven 55%. Edge = 62% − 55% = 7%. This is positive but below the High confidence threshold.',
  },
  {
    title: 'What the Confidence Tiers Mean',
    content: `Confidence tiers summarise the strength of a signal. High confidence means edge is above 15% and the regime is clearly confirmed. Medium means edge is between 8% and 15%, or regime confirmation is partial. Low means edge is between 0% and 8%, or one or more supporting conditions are weak. Low confidence signals appear in Signal Tracker but are rarely recommended as Take.`,
    example: 'Example: Edge +22%, Bullish regime confirmed, RSI momentum favourable → High confidence. Edge +10%, Neutral regime → Medium confidence.',
  },
  {
    title: 'When Not to Trade',
    content: `LIVEWELL issues a no-trade flag when one or more blocking conditions are met. These include: a scheduled high-impact economic event within the expiry window (NFP, CPI, FOMC), abnormally low volatility that compresses edge below meaningful levels, regime ambiguity where trend direction is unclear across timeframes, and negative or near-zero model edge after costs. A no-trade day is not a failure — it is the system working as intended.`,
    example: 'Example: NFP release at 13:30. Any contract expiring at 14:00 is flagged no-trade regardless of model probability.',
  },
];

const HowItWorks = () => (
  <Container maxWidth="md" sx={{ py: 4 }}>
    <Typography variant="h4" component="h1" gutterBottom>
      How It Works
    </Typography>
    <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
      Understand what LIVEWELL computes, how decisions are made, and when not to trade.
    </Typography>
    {SECTIONS.map((s) => (
      <Accordion key={s.title}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontWeight="bold">{s.title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>{s.content}</Typography>
          <Typography variant="body2" color="text.secondary" fontStyle="italic">{s.example}</Typography>
        </AccordionDetails>
      </Accordion>
    ))}
  </Container>
);

export default HowItWorks;
