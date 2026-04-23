import { useState, useMemo } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
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
import { useBacktest } from '../hooks/useBacktest';

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function EquityCurve({ points }: { points: Array<{ date: string; value: number }> }) {
  const W = 600;
  const H = 120;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coords = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * W;
      const y = H - ((p.value - min) / range) * H;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <Box sx={{ overflowX: 'auto', mt: 1 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} aria-label="Equity curve">
        <polyline points={coords} fill="none" stroke="#1976d2" strokeWidth="2" />
      </svg>
    </Box>
  );
}

const BacktestResults = () => {
  const { data, loading, error } = useBacktest();
  const [marketFilter, setMarketFilter] = useState('All');
  const [regimeFilter, setRegimeFilter] = useState('All');
  const [expiryWindowFilter, setExpiryWindowFilter] = useState('All');

  const markets = useMemo(() => {
    if (!data) return [];
    return ['All', ...Array.from(new Set(data.rows.map((r) => r.market)))];
  }, [data]);

  const regimes = useMemo(() => {
    if (!data) return [];
    return ['All', ...Array.from(new Set(data.rows.map((r) => r.regime)))];
  }, [data]);

  const expiryWindows = useMemo(() => {
    if (!data) return [];
    return ['All', ...Array.from(new Set(data.rows.map((r) => r.expiryWindow)))];
  }, [data]);

  const filteredRows = useMemo(() => {
    if (!data) return [];
    return data.rows.filter(
      (r) =>
        (marketFilter === 'All' || r.market === marketFilter) &&
        (regimeFilter === 'All' || r.regime === regimeFilter) &&
        (expiryWindowFilter === 'All' || r.expiryWindow === expiryWindowFilter)
    );
  }, [data, marketFilter, regimeFilter, expiryWindowFilter]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Backtest Results
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Out-of-sample performance by market and regime
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load backtest: {error}</Alert>}

      {!loading && !error && data && (
        <>
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Total Trades', value: String(data.totalTrades) },
              { label: 'Win Rate',     value: pct(data.winRate) },
              { label: 'Avg Edge',     value: pct(data.avgEdge) },
              { label: 'Max Drawdown', value: pct(data.maxDrawdown) },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h4" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ p: 2, mb: 4 }}>
            <Typography variant="h6" gutterBottom>Equity Curve</Typography>
            <EquityCurve points={data.equityCurve} />
          </Paper>

          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="market-filter-label">Market</InputLabel>
              <Select
                labelId="market-filter-label"
                value={marketFilter}
                label="Market"
                onChange={(e) => setMarketFilter(e.target.value)}
              >
                {markets.map((m) => <MenuItem key={m} value={m}>{m}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="regime-filter-label">Regime</InputLabel>
              <Select
                labelId="regime-filter-label"
                value={regimeFilter}
                label="Regime"
                onChange={(e) => setRegimeFilter(e.target.value)}
              >
                {regimes.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="expiry-window-filter-label">Expiry Window</InputLabel>
              <Select
                labelId="expiry-window-filter-label"
                value={expiryWindowFilter}
                label="Expiry Window"
                onChange={(e) => setExpiryWindowFilter(e.target.value)}
              >
                {expiryWindows.map((w) => <MenuItem key={w} value={w}>{w}</MenuItem>)}
              </Select>
            </FormControl>
          </Box>

          <Paper>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Market</TableCell>
                  <TableCell>Regime</TableCell>
                  <TableCell>Expiry Window</TableCell>
                  <TableCell align="right">Trades</TableCell>
                  <TableCell align="right">Win Rate</TableCell>
                  <TableCell align="right">Avg Edge</TableCell>
                  <TableCell align="right">Net Return</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRows.map((row) => (
                  <TableRow key={`${row.market}-${row.regime}-${row.expiryWindow}`}>
                    <TableCell>{row.market}</TableCell>
                    <TableCell>{row.regime}</TableCell>
                    <TableCell>{row.expiryWindow}</TableCell>
                    <TableCell align="right">{row.trades}</TableCell>
                    <TableCell align="right">{pct(row.winRate)}</TableCell>
                    <TableCell align="right">{pct(row.avgEdge)}</TableCell>
                    <TableCell align="right">{pct(row.netReturn)}</TableCell>
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

export default BacktestResults;
