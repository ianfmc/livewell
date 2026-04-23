import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import Paper from '@mui/material/Paper';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Stack from '@mui/material/Stack';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Stepper from '@mui/material/Stepper';
import Typography from '@mui/material/Typography';
import { mockContractDetails } from '../data/mockData';

type AdvisorState = {
  step: 0 | 1 | 2 | 3;
  market: string | null;
  expiryWindow: '2-hour' | 'Daily' | null;
  trend: 'Bullish' | 'Bearish' | 'Neutral' | null;
  volatility: 'Low' | 'Normal' | 'High' | null;
  eventRisk: 'None' | 'Low' | 'High' | null;
};

const INITIAL: AdvisorState = {
  step: 0,
  market: null,
  expiryWindow: null,
  trend: null,
  volatility: null,
  eventRisk: null,
};

const MARKETS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'Gold', 'US 500'];
const STEP_LABELS = ['Select Market', 'Expiry Window', 'Current Regime'];

function candidateExplanation(
  regime: string,
  trend: string,
  volatility: string,
  eventRisk: string
): string {
  const notes: string[] = [];
  if (regime === trend) notes.push(`regime matches selected trend (${trend})`);
  else notes.push(`regime (${regime}) differs from selected trend (${trend})`);
  if (volatility === 'High') notes.push('high volatility selected — spread risk elevated');
  if (eventRisk === 'High') notes.push('high event risk — no-trade conditions may apply');
  return notes.join('; ');
}

const OptionsAdvisor = () => {
  const [state, setState] = useState<AdvisorState>(INITIAL);

  const update = (partial: Partial<AdvisorState>) =>
    setState((s) => ({ ...s, ...partial }));

  const candidates = mockContractDetails.filter(
    (c) => c.instrument === state.market
  );

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Options Advisor
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Answer a few questions to get filtered contract candidates for your current setup.
      </Typography>

      {state.step < 3 && (
        <Stepper activeStep={state.step} sx={{ mb: 4 }}>
          {STEP_LABELS.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      )}

      {state.step === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 1: Select a Market</Typography>
          <FormControl component="fieldset">
            <RadioGroup
              value={state.market ?? ''}
              onChange={(e) => update({ market: e.target.value })}
            >
              {MARKETS.map((m) => (
                <FormControlLabel key={m} value={m} control={<Radio />} label={m} />
              ))}
            </RadioGroup>
          </FormControl>
          <Box sx={{ mt: 3 }}>
            <Button
              variant="contained"
              disabled={!state.market}
              onClick={() => update({ step: 1 })}
            >
              Next
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 2: Select Expiry Window</Typography>
          <FormControl component="fieldset">
            <RadioGroup
              value={state.expiryWindow ?? ''}
              onChange={(e) => update({ expiryWindow: e.target.value as '2-hour' | 'Daily' })}
            >
              <FormControlLabel value="2-hour" control={<Radio />} label="2-hour" />
              <FormControlLabel value="Daily"  control={<Radio />} label="Daily" />
            </RadioGroup>
          </FormControl>
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => update({ step: 0 })}>Back</Button>
            <Button
              variant="contained"
              disabled={!state.expiryWindow}
              onClick={() => update({ step: 2 })}
            >
              Next
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 3: Describe Current Regime</Typography>
          <Stack spacing={3}>
            <FormControl component="fieldset">
              <FormLabel component="legend">Trend Direction</FormLabel>
              <RadioGroup
                row
                value={state.trend ?? ''}
                onChange={(e) => update({ trend: e.target.value as AdvisorState['trend'] })}
              >
                {['Bullish', 'Bearish', 'Neutral'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
            <FormControl component="fieldset">
              <FormLabel component="legend">Volatility</FormLabel>
              <RadioGroup
                row
                value={state.volatility ?? ''}
                onChange={(e) => update({ volatility: e.target.value as AdvisorState['volatility'] })}
              >
                {['Low', 'Normal', 'High'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
            <FormControl component="fieldset">
              <FormLabel component="legend">Event Risk</FormLabel>
              <RadioGroup
                row
                value={state.eventRisk ?? ''}
                onChange={(e) => update({ eventRisk: e.target.value as AdvisorState['eventRisk'] })}
              >
                {['None', 'Low', 'High'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
          </Stack>
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => update({ step: 1 })}>Back</Button>
            <Button
              variant="contained"
              disabled={!state.trend || !state.volatility || !state.eventRisk}
              onClick={() => update({ step: 3 })}
            >
              View Candidates
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 3 && (
        <Box>
          <Typography variant="h6" gutterBottom>Matching Candidates</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Market: {state.market} | Expiry: {state.expiryWindow} | Trend: {state.trend} | Volatility: {state.volatility} | Event Risk: {state.eventRisk}
          </Typography>
          {candidates.length === 0 ? (
            <Paper sx={{ p: 3 }}>
              <Typography variant="body1">No candidates found for {state.market} in current mock data.</Typography>
            </Paper>
          ) : (
            <Stack spacing={2} sx={{ mb: 3 }}>
              {candidates.map((c) => (
                <Card key={`${c.instrument}-${c.strike}`}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight="bold">
                          {c.instrument} @ {c.strike} — {c.expiry}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {candidateExplanation(c.regime, state.trend!, state.volatility!, state.eventRisk!)}
                        </Typography>
                      </Box>
                      <Chip
                        label={c.recommendation}
                        color={c.recommendation === 'Take' ? 'success' : c.recommendation === 'Watch' ? 'warning' : 'default'}
                        size="small"
                      />
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
          <Button variant="outlined" onClick={() => setState(INITIAL)}>Start Over</Button>
        </Box>
      )}
    </Container>
  );
};

export default OptionsAdvisor;
