// src/theme.ts

import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#000000', // Primary = black
      contrastText: '#ffffff',
    },
    background: {
      default: '#f4f6f8',
      paper: '#ffffff',
    },
    text: {
      primary: '#111111',
      secondary: '#666666',
    },
  },
  typography: {
    fontFamily:
      '"IBM Plex Sans", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h5: {
      fontWeight: 700,
      letterSpacing: '-0.2px',
    },
    h6: {
      fontWeight: 700,
      letterSpacing: '-0.1px',
    },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          border: '1px solid #e0e0e0',
          boxShadow: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 700,
          backgroundColor: '#fafafa',
        },
      },
    },
  },
})
