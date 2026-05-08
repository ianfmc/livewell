import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router-dom';

import type { ContractCard as ContractCardData } from '../data/mockData';

type CardProps = ContractCardData;

const ContractCard = ({ instrument, strike, expiry, status }: CardProps) => {
  const navigate = useNavigate();
  const to = `/signals/${instrument.replace(/\//g, '-')}/${strike}`;

  return (
    <Card elevation={3} sx={{ borderRadius: 3 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ textAlign: 'left' }}>{instrument}</Typography>
          <Chip label={status} size="small" />
        </Stack>
        <Stack spacing={0.5} alignItems="flex-start">
          <Typography variant="body1">Strike: {strike}</Typography>
          <Typography variant="body2" color="text.secondary">
            Expires: {expiry}
          </Typography>
        </Stack>
        <Button
          variant="outlined"
          size="small"
          onClick={() => navigate(to)}
          sx={{ mt: 2 }}
        >
          View Details
        </Button>
      </CardContent>
    </Card>
  );
};

export default ContractCard;
