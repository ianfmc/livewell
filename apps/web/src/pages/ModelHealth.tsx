import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useModelHealth } from '../hooks/useModelHealth';

const statusColor = (s: 'Healthy' | 'Warning' | 'Degraded') =>
  s === 'Healthy' ? 'success' : s === 'Warning' ? 'warning' : 'error';

const featureColor = (s: 'Available' | 'Stale' | 'Missing') =>
  s === 'Available' ? 'success' : s === 'Stale' ? 'warning' : 'error';

const ModelHealth = () => {
  const { data, loading, error } = useModelHealth();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Model Health
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Current model status, feature availability, and drift indicators
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load model health: {error}</Alert>}

      {!loading && !error && data && (
        <>
          <Paper sx={{ p: 2, mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6">Overall Status</Typography>
            <Chip
              label={data.overallStatus}
              color={statusColor(data.overallStatus)}
            />
          </Paper>

          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Training Date',       value: data.trainingDate },
              { label: 'Data Freshness',       value: data.dataFreshness },
              { label: 'Calibration Error',    value: data.calibrationError.toFixed(3) },
              { label: 'Validation Accuracy',  value: `${(data.validationAccuracy * 100).toFixed(1)}%` },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h5" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ mb: 4 }}>
            <Typography variant="h6" sx={{ p: 2, pb: 0 }}>Feature Availability</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Feature</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.features.map((f) => (
                  <TableRow key={f.name}>
                    <TableCell>{f.name}</TableCell>
                    <TableCell>
                      <Chip label={f.status} color={featureColor(f.status)} size="small" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Drift Warnings</Typography>
            {data.driftWarnings.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No issues detected.</Typography>
            ) : (
              data.driftWarnings.map((w) => (
                <Alert key={w.feature} severity="warning" sx={{ mb: 1 }} aria-label={w.feature}>
                  {w.description}
                </Alert>
              ))
            )}
          </Paper>
        </>
      )}
    </Container>
  );
};

export default ModelHealth;
