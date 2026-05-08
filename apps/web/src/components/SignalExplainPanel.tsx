import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';
import { useSignalExplain } from '../hooks/useSignalExplain';

type Props = {
  signalId: string | null;
  onClose: () => void;
};

const SECTIONS = [
  { key: 'trend',    label: 'Trend' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'session',  label: 'Session' },
  { key: 'timing',   label: 'Timing' },
] as const;

export function SignalExplainPanel({ signalId, onClose }: Props) {
  const { data, loading, error } = useSignalExplain(signalId);

  if (!signalId) return null;

  return (
    <Box
      data-testid="signal-explain-panel"
      sx={{
        mt: 2,
        p: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        position: 'relative',
        minHeight: 80,
      }}
    >
      <IconButton
        aria-label="close"
        size="small"
        onClick={onClose}
        sx={{ position: 'absolute', top: 8, right: 8 }}
      >
        <CloseIcon fontSize="small" />
      </IconButton>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && data && (
        <Stack spacing={1.5} sx={{ pr: 4 }}>
          <Typography variant="caption" color="text.secondary" fontWeight="bold">
            {data.header}
          </Typography>
          <Divider />
          {SECTIONS.map(({ key, label }) =>
            data[key] ? (
              <Box key={key}>
                <Typography variant="overline" color="text.secondary" lineHeight={1.2}>
                  {label}
                </Typography>
                <Typography variant="body2">{data[key]}</Typography>
              </Box>
            ) : null
          )}
        </Stack>
      )}
    </Box>
  );
}
