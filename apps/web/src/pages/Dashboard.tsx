import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import WarningIcon from '@mui/icons-material/Warning';
import { Link } from 'react-router-dom';

import { useDashboard } from '../hooks/useDashboard';
import type { MarketSnapshot, TopCandidate, ModelHealth, OpportunitySummary } from '../data/mockDashboard';

function MarketConditions({ markets }: { markets: MarketSnapshot[] }) {
  return (
    <Paper sx={{ p: 2, mb: 4 }}>
      <Typography variant="h6" gutterBottom>Market Conditions</Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {markets.map((m) => (
          <Stack key={m.instrument} direction="row" alignItems="center" spacing={0.5}>
            <Chip
              label={`${m.instrument}: ${m.regime}`}
              color={m.regime === 'Bullish' ? 'success' : m.regime === 'Bearish' ? 'error' : 'default'}
            />
            {m.noTrade && (
              <Tooltip title="No trade — avoid this instrument">
                <WarningIcon fontSize="small" color="warning" aria-label="No trade" />
              </Tooltip>
            )}
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

function OpportunitySummarySection({ opportunities }: { opportunities: OpportunitySummary }) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" gutterBottom>Opportunity Summary</Typography>
      {opportunities.passing === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No valid setups today. The system is being selective — this is expected.
        </Alert>
      )}
      <Grid container spacing={2}>
        {[
          { label: 'Total Candidates', value: opportunities.total },
          { label: 'Passing Rules', value: opportunities.passing },
          { label: 'Flagged for Review', value: opportunities.review },
        ].map((item) => (
          <Grid key={item.label} size={{ xs: 12, sm: 4 }}>
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="h3" component="p">{item.value}</Typography>
              <Typography variant="body2" color="text.secondary">{item.label}</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

function TopCandidatesSection({ candidates }: { candidates: TopCandidate[] }) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" gutterBottom>Top Contract Candidates</Typography>
      <Stack spacing={2}>
        {candidates.map((c) => (
          <Card key={`${c.instrument}-${c.strike}`}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
                <Box sx={{ textAlign: 'left' }}>
                  <Typography variant="subtitle1" fontWeight="bold">{c.instrument}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Strike: {c.strike} &nbsp;|&nbsp; Expiry: {(() => {
                      try {
                        return new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(c.expiry));
                      } catch {
                        return c.expiry;
                      }
                    })()}
                  </Typography>
                  <Typography variant="body2">
                    Edge: <strong>{c.edge}</strong> &nbsp;|&nbsp; Confidence: {c.confidence}
                  </Typography>
                </Box>
                <Button<typeof Link> component={Link} to="/signals" variant="outlined" size="small">
                  View All Signals
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Box>
  );
}

function ModelHealthSection({ health }: { health: ModelHealth }) {
  return (
    <Paper sx={{ p: 2, mb: 4 }}>
      <Typography variant="h6" gutterBottom>Model Health</Typography>
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="body2">Training Date: {health.trainingDate}</Typography>
        <Chip
          label={health.dataFreshness}
          color={health.dataFreshness === 'Current' ? 'success' : 'warning'}
          size="small"
        />
        <Chip
          label={health.status}
          color={health.status === 'Healthy' ? 'success' : health.status === 'Warning' ? 'warning' : 'error'}
          size="small"
        />
      </Stack>
    </Paper>
  );
}

const Dashboard = () => {
  const { data, loading, error } = useDashboard();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && data && (
        <>
          <MarketConditions markets={data.markets} />
          <OpportunitySummarySection opportunities={data.opportunities} />
          <TopCandidatesSection candidates={data.topCandidates} />
          <ModelHealthSection health={data.modelHealth} />
        </>
      )}
    </Container>
  );
};

export default Dashboard;
