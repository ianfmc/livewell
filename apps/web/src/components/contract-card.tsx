import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';

import type { ContractCard as ContractCardData } from '../data/mockData';

type CardProps = ContractCardData;

const ContractCard = ({ instrument, strike, expiry, status }: CardProps) => {
  const to = `/signals/${instrument.replace(/\//g, '-')}/${strike}`;

  return (
    <Card elevation={3} sx={{ borderRadius: 3 }}>
      <CardActionArea<typeof RouterLink> component={RouterLink} to={to}>
        <CardContent>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 2 }}
          >
            <Typography variant="h5">{instrument}</Typography>
            <Chip label={status} size="small" />
          </Stack>
          <Stack spacing={0.5} alignItems="flex-start">
            <Typography variant="body1">Strike: {strike}</Typography>
            <Typography variant="body2" color="text.secondary">
              Expires: {expiry}
            </Typography>
          </Stack>
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

export default ContractCard;
