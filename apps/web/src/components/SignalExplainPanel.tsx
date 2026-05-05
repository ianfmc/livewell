import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Typography from '@mui/material/Typography';
import { A2uiSurface } from '@a2ui/react/v0_9';
import { useSignalExplain } from '../hooks/useSignalExplain';

type Props = {
  signalId: string | null;
  onClose: () => void;
};

export function SignalExplainPanel({ signalId, onClose }: Props) {
  const { surface, loading, error } = useSignalExplain(signalId);

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

      {!loading && !error && surface && (
        <Box sx={{ pr: 4 }}>
          <A2uiSurface surface={surface} />
        </Box>
      )}

      {!loading && !error && !surface && (
        <Typography variant="body2" color="text.secondary">
          Generating explanation…
        </Typography>
      )}
    </Box>
  );
}
