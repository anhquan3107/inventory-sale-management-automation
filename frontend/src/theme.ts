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
    },
  },
  shape: {
    borderRadius: 10,
  },
})
