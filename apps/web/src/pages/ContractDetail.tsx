import { Link as RouterLink, useParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { useContractDetail } from '../hooks/useContractDetail';

const ContractDetail = () => {
  const { instrument: encodedInstrument = '', strike = '' } = useParams();
  const instrument = encodedInstrument.replace(/-/g, '/');
  const { data, loading, error } = useContractDetail(instrument, strike);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto', mt: 3, px: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!data) return null;

  const recommendationColor =
    data.recommendation === 'Take' ? 'success' :
    data.recommendation === 'Watch' ? 'warning' : 'default';

  const confidenceColor =
    data.confidence === 'High' ? 'success' :
    data.confidence === 'Medium' ? 'warning' : 'default';

  const edgeFormatted =
    data.edge >= 0
      ? `+${Math.round(data.edge * 100)}%`
      : `${Math.round(data.edge * 100)}%`;

  const modelFormatted = `${Math.round(data.modelProbability * 100)}%`;

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', mt: 3, px: 2 }}>
      <RouterLink
        to="/signals"
        style={{ display: 'block', marginBottom: '16px', textDecoration: 'none' }}
      >
        ← Daily Signals
      </RouterLink>

      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="flex-start"
        sx={{ mb: 1 }}
      >
        <Box>
          <Typography variant="h4">{data.instrument}</Typography>
          <Typography variant="body2" color="text.secondary">
            Strike {data.strike} · Expires {data.expiry}
          </Typography>
        </Box>
        <Chip
          label={data.recommendation.toUpperCase()}
          color={recommendationColor as 'success' | 'warning' | 'default'}
          sx={{ fontWeight: 'bold' }}
        />
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
        <Chip label={data.regime} size="small" color="info" />
        <Chip
          label={`${data.confidence} confidence`}
          size="small"
          color={confidenceColor as 'success' | 'warning' | 'default'}
        />
        {data.noTradeFlag && <Chip label="No Trade" size="small" color="error" />}
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
        {[
          { value: `$${data.economics.cost}`, label: 'Cost' },
          { value: `$${data.economics.payout}`, label: 'Payout' },
          { value: modelFormatted, label: 'Model' },
          { value: edgeFormatted, label: 'Edge' },
        ].map(({ value, label }) => (
          <Box
            key={label}
            sx={{
              flex: 1,
              bgcolor: 'action.hover',
              borderRadius: 1,
              p: 1.5,
              textAlign: 'center',
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color:
                  label === 'Edge'
                    ? data.edge < 0
                      ? 'error.main'
                      : 'success.main'
                    : 'inherit',
              }}
            >
              {value}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
          </Box>
        ))}
      </Stack>

      <Box sx={{ mb: 2 }}>
        <Typography variant="overline" color="text.secondary">
          Why this setup
        </Typography>
        <Stack spacing={0.5} sx={{ mt: 0.5 }}>
          {data.reasonCodes.map((r) => (
            <Typography key={r.label} variant="body2">
              {r.positive ? '✓' : '✗'} {r.label}
            </Typography>
          ))}
        </Stack>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
        {data.rationale}
      </Typography>
    </Box>
  );
};

export default ContractDetail;
