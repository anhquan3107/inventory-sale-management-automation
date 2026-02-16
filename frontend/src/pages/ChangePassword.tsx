import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  CssBaseline,
  FormControl,
  FormLabel,
  Stack,
  TextField,
  Typography,
  Card as MuiCard,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import { authApi } from '../api/auth'

const Card = styled(MuiCard)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignSelf: 'center',
  width: '100%',
  maxWidth: 450,
  padding: theme.spacing(4),
  gap: theme.spacing(2),
  boxShadow:
    'hsla(220, 30%, 5%, 0.05) 0px 5px 15px 0px, hsla(220, 25%, 10%, 0.05) 0px 15px 35px -5px',
}))

const Container = styled(Stack)(({ theme }) => ({
  minHeight: '100vh',
  padding: theme.spacing(2),
  justifyContent: 'center',
  alignItems: 'center',
  position: 'relative',
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    zIndex: -1,
    background:
      'radial-gradient(ellipse at center, hsl(210, 100%, 97%), hsl(0, 0%, 100%))',
  },
}))

const ChangePassword = () => {
  const navigate = useNavigate()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters long.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.')
      return
    }

    if (currentPassword === newPassword) {
      setError('New password must be different from current password.')
      return
    }

    try {
      setSubmitting(true)
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      navigate('/dashboard', { replace: true })
    } catch {
      setError('Failed to change password. Please check your current password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <CssBaseline />
      <Container direction='column'>
        <Card variant='outlined'>
          <Typography variant='h4'>Change Password</Typography>
          <Typography variant='body2' color='text.secondary'>
            You must change your password before continuing.
          </Typography>

          {error && <Alert severity='error'>{error}</Alert>}

          <Box
            component='form'
            onSubmit={handleSubmit}
            sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
          >
            <FormControl>
              <FormLabel htmlFor='current-password'>Current Password</FormLabel>
              <TextField
                id='current-password'
                type='password'
                placeholder='Enter current password'
                fullWidth
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel htmlFor='new-password'>New Password</FormLabel>
              <TextField
                id='new-password'
                type='password'
                placeholder='Enter new password'
                fullWidth
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </FormControl>

            <FormControl>
              <FormLabel htmlFor='confirm-password'>
                Confirm New Password
              </FormLabel>
              <TextField
                id='confirm-password'
                type='password'
                placeholder='Confirm new password'
                fullWidth
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </FormControl>

            <Button
              type='submit'
              fullWidth
              variant='contained'
              disabled={submitting}
            >
              Change Password
            </Button>
          </Box>
        </Card>
      </Container>
    </>
  )
}

export default ChangePassword
