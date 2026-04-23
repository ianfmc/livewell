import { useState } from 'react';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Typography from '@mui/material/Typography';

import ContractCard from '../components/contract-card';
import { useSignals } from '../hooks/useSignals';

const DailySignals = () => {
  const [statusFilter, setStatusFilter] = useState('All');
  const { data, loading, error } = useSignals();

  const filteredData = statusFilter === 'All' ? data : data.filter(item => item.status === statusFilter);

  return(
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Daily Signals
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Review scored opportunities, filter by status, and inspect contracts
        </Typography>

      <Box sx={{ mb: 3, maxWidth: 222 }}>
        <FormControl fullWidth size="small">
          <InputLabel id="status-filter-label">Status</InputLabel>
          <Select
            labelId="status-filter-label"
            id="status-filter"
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="All">All</MenuItem>
            <MenuItem value="Open">Open</MenuItem>
            <MenuItem value="Review">Review</MenuItem>
            <MenuItem value="Closed">Closed</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load signals: {error}
        </Alert>
      )}

      {!loading && !error && (
        <>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Visible Contracts: {filteredData.length} | Review Needed: {" "}
            {filteredData.filter(item => item.status === 'Review').length}
          </Typography>

          <Grid container spacing={3}>
            {filteredData.map((card) => (
              <Grid size={{ xs:12, sm:6, md: 4}} key={card.instrument + card.strike}>
                <ContractCard
                instrument={card.instrument}
                strike={card.strike}
                expiry={card.expiry}
                status={card.status}
              />
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Container>
  );
}

export default DailySignals;  