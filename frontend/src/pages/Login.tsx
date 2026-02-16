import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Checkbox,
  CssBaseline,
  FormControl,
  FormControlLabel,
  FormLabel,
  Link,
  Stack,
  TextField,
  Typography,
  Card as MuiCard,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  OutlinedInput,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import { useAuth } from '../hooks/use-auth'

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

const SignInContainer = styled(Stack)(({ theme }) => ({
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

const Login = () => {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [usernameError, setUsernameError] = useState(false)
  const [usernameErrorMessage, setUsernameErrorMessage] = useState('')
  const [passwordError, setPasswordError] = useState(false)
  const [passwordErrorMessage, setPasswordErrorMessage] = useState('')
  const [forgotOpen, setForgotOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const validateInputs = (): boolean => {
    const username = document.getElementById('username') as HTMLInputElement
    const password = document.getElementById('password') as HTMLInputElement

    let isValid = true

    if (!username.value || username.value.trim().length < 3) {
      setUsernameError(true)
      setUsernameErrorMessage('Please enter a valid username or email.')
      isValid = false
    } else {
      setUsernameError(false)
      setUsernameErrorMessage('')
    }

    if (!password.value || password.value.length < 6) {
      setPasswordError(true)
      setPasswordErrorMessage('Password must be at least 6 characters long.')
      isValid = false
    } else {
      setPasswordError(false)
      setPasswordErrorMessage('')
    }

    return isValid
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!validateInputs()) return

    const data = new FormData(event.currentTarget)
    const identifier = data.get('username') as string
    const password = data.get('password') as string

    try {
      setSubmitting(true)
      const result = await login(identifier, password)

      if (result.must_change_password) {
        navigate('/change-password', { replace: true })
      } else {
        navigate('/dashboard', { replace: true })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <CssBaseline />
      <SignInContainer direction='column'>
        <Card variant='outlined'>
          <Typography variant='h4'>Sign in</Typography>

          <Box
            component='form'
            onSubmit={handleSubmit}
            sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
          >
            <FormControl>
              <FormLabel htmlFor='username'>Username or Email</FormLabel>
              <TextField
                id='username'
                name='username'
                placeholder='Enter your username or email'
                fullWidth
                required
                error={usernameError}
                helperText={usernameErrorMessage}
              />
            </FormControl>

            <FormControl>
              <FormLabel htmlFor='password'>Password</FormLabel>
              <TextField
                id='password'
                name='password'
                type='password'
                placeholder='••••••'
                fullWidth
                required
                error={passwordError}
                helperText={passwordErrorMessage}
              />
            </FormControl>

            <FormControlLabel
              control={<Checkbox color='primary' />}
              label='Remember me'
            />

            <Button
              type='submit'
              fullWidth
              variant='contained'
              disabled={submitting}
            >
              Sign in
            </Button>

            <Link
              component='button'
              variant='body2'
              onClick={() => setForgotOpen(true)}
              sx={{ alignSelf: 'center' }}
            >
              Forgot your password?
            </Link>
          </Box>
        </Card>
      </SignInContainer>

      <Dialog open={forgotOpen} onClose={() => setForgotOpen(false)}>
        <DialogTitle>Reset password</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Enter your email address and we’ll send a reset link.
          </DialogContentText>
          <OutlinedInput
            fullWidth
            required
            type='email'
            placeholder='Email address'
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setForgotOpen(false)}>Cancel</Button>
          <Button variant='contained'>Continue</Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default Login
