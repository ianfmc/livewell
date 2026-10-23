import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';

import type { ContractCard as ContractCardData } from '../data/mockData';

type CardProps = ContractCardData;

const CONFIDENCE_COLOR = {
  High: 'success',
  Medium: 'warning',
  Low: 'default',
} as const;

const fmt = (v: number | null, digits = 4) =>
  v === null || v === undefined ? '—' : v.toFixed(digits);

const ContractCard = ({
  instrument, strike, expiry, status, direction, date,
  confidence, scoreAvailable, edge, supportingSignals, reasonCodes,
}: CardProps) => {
  const to = `/signals/${instrument.replace(/\//g, '-')}/${strike}`;
  const dirLabel = direction === 'none' ? 'No direction' : direction.toUpperCase();

  return (
    <Card elevation={3} sx={{ borderRadius: 3 }}>
      <CardActionArea<typeof RouterLink> component={RouterLink} to={to}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="h5" sx={{ textAlign: 'left' }}>{instrument}</Typography>
            <Chip label={status} size="small" />
          </Stack>

          <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} alignItems="center">
            <Chip label={dirLabel} size="small" color={direction === 'buy' ? 'success' : direction === 'sell' ? 'error' : 'default'} variant="outlined" />
            <Chip
              label={scoreAvailable ? `${confidence} confidence` : `${confidence} (rule-based)`}
              size="small"
              color={CONFIDENCE_COLOR[confidence]}
            />
            {scoreAvailable && (
              <Typography variant="caption" color="text.secondary">
                edge {edge >= 0 ? '+' : ''}{(edge * 100).toFixed(1)}%
              </Typography>
            )}
          </Stack>

          <Stack spacing={0.5} alignItems="flex-start" sx={{ mb: 1.5 }}>
            <Typography variant="body1">Strike: {strike}</Typography>
            <Typography variant="body2" color="text.secondary">Expires: {expiry}</Typography>
            <Typography variant="caption" color="text.secondary">As of: {date}</Typography>
          </Stack>

          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'left' }}>
            EMA20 {fmt(supportingSignals.ema20)} · EMA50 {fmt(supportingSignals.ema50)} · RSI {fmt(supportingSignals.rsi14, 1)} · MACDh {fmt(supportingSignals.macdHist, 4)} · ATR {fmt(supportingSignals.atr14, 4)}
          </Typography>

          {reasonCodes.length > 0 && (
            <Stack spacing={0.25} alignItems="flex-start" sx={{ mt: 1 }}>
              {reasonCodes.slice(0, 3).map((rc, i) => (
                <Typography key={i} variant="caption" color={rc.positive ? 'success.main' : 'text.secondary'}>
                  {rc.positive ? '✓' : '✗'} {rc.label}
                </Typography>
              ))}
            </Stack>
          )}
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

export default ContractCard;
