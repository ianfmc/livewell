import { useState } from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CssBaseline from '@mui/material/CssBaseline';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import MenuIcon from '@mui/icons-material/Menu';
import { Link, Route, Routes } from 'react-router-dom';

import ContractDetail from './pages/ContractDetail';
import Dashboard from './pages/Dashboard';
import DailySignals from './pages/DailySignals';
import { useTheme } from './components/theme-provider';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/' },
  { label: 'Daily Signals', path: '/signals' },
];

const App = () => {
  const { theme, setTheme } = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <CssBaseline />
      <Box
        sx={{
          flexGrow: 1,
          minHeight: '100vh',
          bgcolor: theme === 'light' ? 'grey.100' : 'grey.900',
          color: theme === 'light' ? 'text.primary' : '#fff',
        }}
      >
        <AppBar
          position="static"
          color="transparent"
          sx={{ bgcolor: theme === 'light' ? 'primary.main' : 'grey.900' }}
        >
          <Toolbar>
            <IconButton
              edge="start"
              aria-label="menu"
              onClick={() => setDrawerOpen(true)}
              sx={{ mr: 2, color: '#FFFFFF' }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ color: '#FFFFFF', flexGrow: 1 }}>
              LIVEWELL
            </Typography>
            <Button
              variant="contained"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              Toggle Theme ({theme})
            </Button>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="temporary"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box component="nav" sx={{ width: 240, pt: 1 }} aria-label="navigation drawer">
            <Divider />
            <List>
              {NAV_ITEMS.map(({ label, path }) => (
                <ListItemButton<typeof Link>
                  key={path}
                  component={Link}
                  to={path}
                  onClick={() => setDrawerOpen(false)}
                >
                  <ListItemText primary={label} />
                </ListItemButton>
              ))}
            </List>
          </Box>
        </Drawer>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<DailySignals />} />
          <Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
        </Routes>
      </Box>
    </>
  );
};

export default App;
