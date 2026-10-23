import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';
import type { ReactNode } from 'react';

import type { ContractCard as ContractCardData } from '../data/mockData';

type CardProps = ContractCardData & { action?: ReactNode };

const CONFIDENCE_COLOR = {
  High: 'success',
  Medium: 'warning',
  Low: 'default',
} as const;

const fmt = (v: number | null, digits = 4) =>
  v === null || v === undefined ? '—' : v.toFixed(digits);

// A candidate is "actionable" when it has a real direction (not "none").
// Actionable cards get a left accent and a prominent status so the few that
// matter stand out from the many "No direction / Closed" rows (D5/D7).
const ContractCard = ({
  instrument, strike, expiry, status, direction, date,
  confidence, scoreAvailable, edge, supportingSignals, reasonCodes, action,
}: CardProps) => {
  const to = `/signals/${instrument.replace(/\//g, '-')}/${strike}`;
  const actionable = direction === 'buy' || direction === 'sell';
  const accent = direction === 'buy' ? 'success.main' : direction === 'sell' ? 'error.main' : undefined;

  return (
    <Card
      elevation={actionable ? 4 : 1}
      sx={{
        borderRadius: 3,
        borderLeft: actionable ? 4 : 0,
        borderLeftColor: accent,
        opacity: actionable ? 1 : 0.92,
      }}
    >
      <CardActionArea<typeof RouterLink> component={RouterLink} to={to}>
        <CardContent>
          {/* Header: instrument + status (status only emphasized when actionable) */}
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="h6" sx={{ textAlign: 'left', fontWeight: 600 }}>{instrument}</Typography>
            <Chip
              label={status}
              size="small"
              color={actionable ? 'primary' : 'default'}
              variant={actionable ? 'filled' : 'outlined'}
            />
          </Stack>

          {/* Primary read: direction + confidence (D5 — these lead) */}
          <Stack direction="row" spacing={1} sx={{ mb: 1.5, flexWrap: 'nowrap' }} alignItems="center">
            <Chip
              label={direction === 'none' ? 'No direction' : direction.toUpperCase()}
              size="small"
              color={direction === 'buy' ? 'success' : direction === 'sell' ? 'error' : 'default'}
              variant="outlined"
            />
            <Chip
              label={
                actionable
                  ? (scoreAvailable ? `${confidence} confidence` : `${confidence} · rule-based`)
                  : (scoreAvailable ? `Model ${confidence} · not actionable` : 'Not actionable')
              }
              size="small"
              color={actionable ? CONFIDENCE_COLOR[confidence] : 'default'}
              variant={actionable ? 'filled' : 'outlined'}
            />
          </Stack>

          {/* Strike, and a timestamp. Expiry row only shown when meaningful (D6). */}
          <Stack spacing={0.25} alignItems="flex-start" sx={{ mb: 1.5 }}>
            <Typography variant="body1">Strike: {strike}</Typography>
            {expiry && expiry !== 'unscheduled' && (
              <Typography variant="body2" color="text.secondary">Expires: {expiry}</Typography>
            )}
            <Typography variant="caption" color="text.secondary">
              As of {date}{scoreAvailable ? ` · edge ${edge >= 0 ? '+' : ''}${(edge * 100).toFixed(1)}%` : ''}
            </Typography>
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
      {/* Explain action lives inside the card (D4) so it reads as part of it. */}
      {action && <Box sx={{ px: 2, pb: 1 }}>{action}</Box>}
    </Card>
  );
};

export default ContractCard;
