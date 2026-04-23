import { useState, useMemo } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useSignalTracker } from '../hooks/useSignalTracker';
import type { TrackedSignal } from '../data/mockSignalTracker';

const recColor = (r: TrackedSignal['recommendation']) =>
  r === 'Take' ? 'success' : r === 'Watch' ? 'warning' : 'default';

const outcomeColor = (o: TrackedSignal['outcome']) =>
  o === 'Win' ? 'success' : o === 'Loss' ? 'error' : 'default';

const SignalTracker = () => {
  const { data, loading, error } = useSignalTracker();
  const [recFilter, setRecFilter] = useState('All');
  const [outcomeFilter, setOutcomeFilter] = useState('All');

  const filteredData = useMemo(() => {
    return data.filter(
      (s) =>
        (recFilter === 'All' || s.recommendation === recFilter) &&
        (outcomeFilter === 'All' || s.outcome === outcomeFilter)
    );
  }, [data, recFilter, outcomeFilter]);

  const taken = data.filter((s) => s.actionTaken === 'Taken');
  const wins = taken.filter((s) => s.outcome === 'Win');
  const pending = data.filter((s) => s.outcome === 'Pending');
  const winRate = taken.length > 0 ? `${Math.round((wins.length / taken.length) * 100)}%` : '—';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Signal Tracker
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Every scored opportunity, what was taken, and realized outcomes
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load tracker: {error}</Alert>}

      {!loading && !error && (
        <>
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Total Signals',       value: String(data.length) },
              { label: 'Taken',               value: String(taken.length) },
              { label: 'Win Rate (Taken)',     value: winRate },
              { label: 'Pending',             value: String(pending.length) },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h4" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="rec-filter-label">Recommendation</InputLabel>
              <Select
                labelId="rec-filter-label"
                value={recFilter}
                label="Recommendation"
                onChange={(e) => setRecFilter(e.target.value)}
              >
                {['All', 'Take', 'Watch', 'Pass'].map((v) => (
                  <MenuItem key={v} value={v}>{v}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="outcome-filter-label">Outcome</InputLabel>
              <Select
                labelId="outcome-filter-label"
                value={outcomeFilter}
                label="Outcome"
                onChange={(e) => setOutcomeFilter(e.target.value)}
              >
                {['All', 'Win', 'Loss', 'Pending'].map((v) => (
                  <MenuItem key={v} value={v}>{v}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Paper>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Market</TableCell>
                  <TableCell>Strike</TableCell>
                  <TableCell>Expiry</TableCell>
                  <TableCell>Recommendation</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell>Outcome</TableCell>
                  <TableCell align="right">Edge</TableCell>
                  <TableCell align="right">Model Prob</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredData.map((s, i) => (
                  <TableRow key={i}>
                    <TableCell>{s.date}</TableCell>
                    <TableCell>{s.market}</TableCell>
                    <TableCell>{s.strike}</TableCell>
                    <TableCell>{s.expiry}</TableCell>
                    <TableCell>
                      <Chip label={s.recommendation} color={recColor(s.recommendation)} size="small" />
                    </TableCell>
                    <TableCell>{s.actionTaken ?? '—'}</TableCell>
                    <TableCell>
                      <Chip label={s.outcome} color={outcomeColor(s.outcome)} size="small" />
                    </TableCell>
                    <TableCell align="right">{(s.edge * 100).toFixed(0)}%</TableCell>
                    <TableCell align="right">{(s.modelProbability * 100).toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </Container>
  );
};

export default SignalTracker;
