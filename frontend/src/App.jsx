import { useEffect, useState } from 'react'
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from 'react-router-dom'

import {
  changePassword,
  confirmPasswordReset,
  createCase,
  fetchCurrentUser,
  login,
  logout,
  previewCompensation,
  requestPasswordReset,
  searchAirports,
} from './api'

const SESSION_STORAGE_KEY = 'airassist-session'

function readStoredSession() {
  const rawSession = window.localStorage.getItem(SESSION_STORAGE_KEY)
  if (!rawSession) {
    return { token: '', user: null }
  }

  try {
    return JSON.parse(rawSession)
  } catch {
    return { token: '', user: null }
  }
}

function writeStoredSession(session) {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

function clearStoredSession() {
  window.localStorage.removeItem(SESSION_STORAGE_KEY)
}

function AppShell() {
  const navigate = useNavigate()
  const location = useLocation()
  const [session, setSession] = useState(() => readStoredSession())
  const [sessionStatus, setSessionStatus] = useState(() =>
    readStoredSession().token ? 'loading' : 'idle',
  )

  useEffect(() => {
    if (!session.token) {
      return
    }

    let isActive = true
    fetchCurrentUser(session.token)
      .then((user) => {
        if (!isActive) {
          return
        }
        const nextSession = { token: session.token, user }
        setSession(nextSession)
        writeStoredSession(nextSession)
        setSessionStatus('ready')
      })
      .catch(() => {
        if (!isActive) {
          return
        }
        clearStoredSession()
        setSession({ token: '', user: null })
        setSessionStatus('idle')
      })

    return () => {
      isActive = false
    }
  }, [session.token])

  useEffect(() => {
    if (session.user?.must_change_password && location.pathname !== '/change-password') {
      navigate('/change-password')
    }
  }, [location.pathname, navigate, session.user])

  function updateSession(nextSession) {
    setSessionStatus(nextSession.token ? 'ready' : 'idle')
    setSession(nextSession)
    writeStoredSession(nextSession)
  }

  async function handleLogout() {
    if (session.token) {
      try {
        await logout(session.token)
      } catch {
        // Keep logout resilient even if the token was already invalidated.
      }
    }

    clearStoredSession()
    setSession({ token: '', user: null })
    navigate('/')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AirAssist Frontend Start</p>
          <h1>Passenger intake and account recovery</h1>
          <p className="lede">
            Backend-connected screens for email login, temporary-password rotation, reset-password,
            and compensation case creation.
          </p>
        </div>
        <nav className="topbar-actions">
          <Link to="/">Home</Link>
          <Link to="/case/new">New Case</Link>
          {session.user ? (
            <button type="button" className="secondary-button" onClick={handleLogout}>
              Log out
            </button>
          ) : null}
        </nav>
      </header>

      <Routes>
        <Route
          path="/"
          element={
            <HomePage
              session={session}
              sessionStatus={sessionStatus}
              onSessionChange={updateSession}
            />
          }
        />
        <Route
          path="/change-password"
          element={<ChangePasswordPage session={session} onSessionChange={updateSession} />}
        />
        <Route path="/reset-password" element={<ResetPasswordPage onSessionChange={updateSession} />} />
        <Route path="/case/new" element={<CaseCreatePage session={session} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

function HomePage({ onSessionChange, session, sessionStatus }) {
  const navigate = useNavigate()
  const [loginForm, setLoginForm] = useState({ email: '', password: '' })
  const [resetEmail, setResetEmail] = useState('')
  const [loginState, setLoginState] = useState({ busy: false, error: '', success: '' })
  const [resetState, setResetState] = useState({ busy: false, error: '', success: '' })

  async function handleLoginSubmit(event) {
    event.preventDefault()
    setLoginState({ busy: true, error: '', success: '' })
    try {
      const payload = await login(loginForm)
      onSessionChange(payload)
      setLoginState({ busy: false, error: '', success: 'Signed in successfully.' })
      navigate(payload.user.must_change_password ? '/change-password' : '/case/new')
    } catch (error) {
      setLoginState({ busy: false, error: error.message, success: '' })
    }
  }

  async function handleResetRequest(event) {
    event.preventDefault()
    setResetState({ busy: true, error: '', success: '' })
    try {
      const payload = await requestPasswordReset(resetEmail)
      setResetState({ busy: false, error: '', success: payload.detail })
    } catch (error) {
      setResetState({ busy: false, error: error.message, success: '' })
    }
  }

  return (
    <main className="page-grid">
      <section className="hero-card">
        <p className="hero-kicker">Backend status</p>
        <h2>{session.user ? `Signed in as ${session.user.email}` : 'Ready for passenger sign-in'}</h2>
        <p>
          Anonymous passengers can still create a case from the form. Registered passengers can
          sign in here with their email and continue into the same case flow. Auto-created
          passenger accounts must change the emailed temporary password on first login.
        </p>
        <div className="callouts">
          <article>
            <span className="callout-label">Auth mode</span>
            <strong>{session.user ? 'Token session active' : 'Public + authenticated intake'}</strong>
          </article>
          <article>
            <span className="callout-label">Session check</span>
            <strong>{sessionStatus === 'loading' ? 'Refreshing user...' : 'Backend reachable'}</strong>
          </article>
        </div>
      </section>

      <section className="stack-card">
        <article className="panel">
          <h3>Passenger login</h3>
          <p className="helper-text">
            Use the email address from your case and the temporary password sent by AirAssist after
            the case is stored.
          </p>
          <form className="form-stack" onSubmit={handleLoginSubmit}>
            <label>
              Email
              <input
                type="email"
                value={loginForm.email}
                onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={loginForm.password}
                onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
                required
              />
            </label>
            <button type="submit" disabled={loginState.busy}>
              {loginState.busy ? 'Signing in...' : 'Sign in'}
            </button>
            {loginState.error ? <p className="feedback error">{loginState.error}</p> : null}
            {loginState.success ? <p className="feedback success">{loginState.success}</p> : null}
          </form>
        </article>

        <article className="panel">
          <h3>Password reset email</h3>
          <form className="form-stack" onSubmit={handleResetRequest}>
            <label>
              Account email
              <input
                type="email"
                value={resetEmail}
                onChange={(event) => setResetEmail(event.target.value)}
                required
              />
            </label>
            <button type="submit" disabled={resetState.busy}>
              {resetState.busy ? 'Sending...' : 'Send reset link'}
            </button>
            {resetState.error ? <p className="feedback error">{resetState.error}</p> : null}
            {resetState.success ? <p className="feedback success">{resetState.success}</p> : null}
          </form>
        </article>
      </section>
    </main>
  )
}

function ChangePasswordPage({ onSessionChange, session }) {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    new_password_confirmation: '',
  })
  const [state, setState] = useState({ busy: false, error: '', success: '' })

  if (!session.token || !session.user) {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setState({ busy: true, error: '', success: '' })
    try {
      const payload = await changePassword(session.token, form)
      onSessionChange({ token: payload.token, user: payload.user })
      setState({ busy: false, error: '', success: payload.detail })
      navigate('/case/new')
    } catch (error) {
      setState({ busy: false, error: error.message, success: '' })
    }
  }

  return (
    <main className="single-card-page">
      <section className="panel wide-panel">
        <h2>Change your temporary password</h2>
        <p>
          Your account was auto-created from a compensation case. Set a permanent password before
          using the rest of the passenger portal.
        </p>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Current password
            <input
              type="password"
              value={form.current_password}
              onChange={(event) => setForm({ ...form, current_password: event.target.value })}
              required
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={form.new_password}
              onChange={(event) => setForm({ ...form, new_password: event.target.value })}
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              value={form.new_password_confirmation}
              onChange={(event) => setForm({ ...form, new_password_confirmation: event.target.value })}
              required
            />
          </label>
          <button type="submit" disabled={state.busy}>
            {state.busy ? 'Saving...' : 'Update password'}
          </button>
          {state.error ? <p className="feedback error">{state.error}</p> : null}
          {state.success ? <p className="feedback success">{state.success}</p> : null}
        </form>
      </section>
    </main>
  )
}

function ResetPasswordPage({ onSessionChange }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [form, setForm] = useState({
    uid: searchParams.get('uid') || '',
    token: searchParams.get('token') || '',
    new_password: '',
    new_password_confirmation: '',
  })
  const [state, setState] = useState({ busy: false, error: '', success: '' })

  async function handleSubmit(event) {
    event.preventDefault()
    setState({ busy: true, error: '', success: '' })
    try {
      const payload = await confirmPasswordReset(form)
      onSessionChange({ token: payload.token, user: payload.user })
      setState({ busy: false, error: '', success: payload.detail })
      navigate('/case/new')
    } catch (error) {
      setState({ busy: false, error: error.message, success: '' })
    }
  }

  return (
    <main className="single-card-page">
      <section className="panel wide-panel">
        <h2>Reset password</h2>
        <p>
          This screen consumes the `uid` and `token` query params sent by the Django reset email.
        </p>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Reset token
            <input
              type="text"
              value={form.token}
              onChange={(event) => setForm({ ...form, token: event.target.value })}
              required
            />
          </label>
          <label>
            UID
            <input
              type="text"
              value={form.uid}
              onChange={(event) => setForm({ ...form, uid: event.target.value })}
              required
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={form.new_password}
              onChange={(event) => setForm({ ...form, new_password: event.target.value })}
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              value={form.new_password_confirmation}
              onChange={(event) => setForm({ ...form, new_password_confirmation: event.target.value })}
              required
            />
          </label>
          <button type="submit" disabled={state.busy}>
            {state.busy ? 'Resetting...' : 'Reset password'}
          </button>
          {state.error ? <p className="feedback error">{state.error}</p> : null}
          {state.success ? <p className="feedback success">{state.success}</p> : null}
        </form>
      </section>
    </main>
  )
}

function CaseCreatePage({ session }) {
  const [passenger, setPassenger] = useState(() => defaultPassenger(session.user))
  const [flightSegments, setFlightSegments] = useState([createFlightSegment(1, true)])
  const [disruptionDetails, setDisruptionDetails] = useState(() => defaultDisruptionDetails())
  const [documents, setDocuments] = useState({ boardingPass: null, idDocument: null })
  const [airportQuery, setAirportQuery] = useState('')
  const [airportResults, setAirportResults] = useState([])
  const [airportState, setAirportState] = useState({ busy: false, error: '' })
  const [compensationPreview, setCompensationPreview] = useState({
    busy: false,
    error: '',
    data: null,
  })
  const [submitState, setSubmitState] = useState({ busy: false, error: '', success: '' })

  const sortedSegments = [...flightSegments].sort((left, right) => left.sequence_number - right.sequence_number)
  const departureAirportCode = sortedSegments[0]?.departure_airport_code?.trim() ?? ''
  const arrivalAirportCode = sortedSegments.at(-1)?.arrival_airport_code?.trim() ?? ''

  useEffect(() => {
    if (departureAirportCode.length !== 3 || arrivalAirportCode.length !== 3) {
      return undefined
    }

    let isActive = true
    const timeoutId = window.setTimeout(async () => {
      setCompensationPreview((currentState) => ({
        ...currentState,
        busy: true,
        error: '',
      }))

      try {
        const payload = await previewCompensation({
          departure_airport_code: departureAirportCode,
          arrival_airport_code: arrivalAirportCode,
        })
        if (!isActive) {
          return
        }
        setCompensationPreview({ busy: false, error: '', data: payload })
      } catch (error) {
        if (!isActive) {
          return
        }
        setCompensationPreview({ busy: false, error: error.message, data: null })
      }
    }, 350)

    return () => {
      isActive = false
      window.clearTimeout(timeoutId)
    }
  }, [arrivalAirportCode, departureAirportCode])

  function clearCompensationPreview() {
    setCompensationPreview({ busy: false, error: '', data: null })
  }

  function updateFlightSegment(index, fieldName, value) {
    if (fieldName === 'departure_airport_code' || fieldName === 'arrival_airport_code') {
      clearCompensationPreview()
    }
    setFlightSegments((currentSegments) =>
      currentSegments.map((segment, segmentIndex) => {
        if (segmentIndex !== index) {
          return segment
        }
        return { ...segment, [fieldName]: value }
      }),
    )
  }

  function markProblemFlight(index) {
    setFlightSegments((currentSegments) =>
      currentSegments.map((segment, segmentIndex) => ({
        ...segment,
        is_problem_flight: segmentIndex === index,
      })),
    )
  }

  function addConnectingFlight() {
    clearCompensationPreview()
    setFlightSegments((currentSegments) => {
      if (currentSegments.length >= 5) {
        return currentSegments
      }
      return [...currentSegments, createFlightSegment(currentSegments.length + 1, false)]
    })
  }

  function removeFlight(index) {
    clearCompensationPreview()
    setFlightSegments((currentSegments) =>
      currentSegments
        .filter((_, segmentIndex) => segmentIndex !== index)
        .map((segment, segmentIndex) => ({
          ...segment,
          sequence_number: segmentIndex + 1,
          is_problem_flight:
            currentSegments[index]?.is_problem_flight && segmentIndex === 0
              ? true
              : segment.is_problem_flight,
        })),
    )
  }

  async function handleAirportLookup(event) {
    event?.preventDefault()
    setAirportState({ busy: true, error: '' })
    try {
      const results = await searchAirports(airportQuery)
      setAirportResults(results)
      setAirportState({ busy: false, error: '' })
    } catch (error) {
      setAirportResults([])
      setAirportState({ busy: false, error: error.message })
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const disruptionError = getDisruptionValidationError(disruptionDetails)
    if (disruptionError) {
      setSubmitState({ busy: false, error: disruptionError, success: '' })
      return
    }

    setSubmitState({ busy: true, error: '', success: '' })

    const formData = new FormData()
    formData.append('passenger', JSON.stringify(passenger))
    formData.append('gdpr_consent', String(passenger.gdpr_consent))
    formData.append('flight_segments', JSON.stringify(flightSegments))
    formData.append('disruption_details', JSON.stringify(disruptionDetails))

    if (documents.boardingPass) {
      formData.append('document_types', 'BOARDING_PASS')
      formData.append('document_files', documents.boardingPass)
    }

    if (documents.idDocument) {
      formData.append('document_types', 'ID_OR_PASSPORT')
      formData.append('document_files', documents.idDocument)
    }

    try {
      const payload = await createCase(session.token, formData)
      setCompensationPreview({
        busy: false,
        error: '',
        data: {
          orthodromic_distance_km: payload.orthodromic_distance_km,
          compensation_amount_eur: payload.compensation_amount_eur,
          departure_airport_code: payload.flight_segments[0]?.departure_airport_code,
          arrival_airport_code: payload.flight_segments.at(-1)?.arrival_airport_code,
        },
      })
      setSubmitState({
        busy: false,
        error: '',
        success:
          `Case #${payload.id} created on ${new Date(payload.created_at).toLocaleString()}. ` +
          `Status: ${payload.status}. Colleague: ${payload.colleague ?? 'Unassigned'}. ` +
          `Distance: ${payload.orthodromic_distance_km} km. Compensation: €${payload.compensation_amount_eur}.`,
      })
    } catch (error) {
      setSubmitState({ busy: false, error: error.message, success: '' })
    }
  }

  return (
    <main className="case-page">
      <section className="panel panel-wide">
        <div className="section-header">
          <div>
            <p className="eyebrow">CASE_01 / CASE_02 / CASE_03 / CASE_04</p>
            <h2>Create a compensation case</h2>
          </div>
          <span className="status-pill">Transactional case creation enabled</span>
        </div>

        <form className="case-form" onSubmit={handleSubmit}>
          <div className="form-section-grid">
            <section className="subpanel">
              <h3>Passenger details</h3>
              <label>
                First name
                <input
                  type="text"
                  value={passenger.first_name}
                  onChange={(event) => setPassenger({ ...passenger, first_name: event.target.value })}
                  required
                />
              </label>
              <label>
                Last name
                <input
                  type="text"
                  value={passenger.last_name}
                  onChange={(event) => setPassenger({ ...passenger, last_name: event.target.value })}
                  required
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={passenger.email}
                  onChange={(event) => setPassenger({ ...passenger, email: event.target.value })}
                  required
                />
              </label>
            </section>

            <section className="subpanel">
              <h3>Email & compliance</h3>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={passenger.gdpr_consent}
                  onChange={(event) =>
                    setPassenger({ ...passenger, gdpr_consent: event.target.checked })
                  }
                  required
                />
                I agree to the GDPR consent policy for claim processing.
              </label>
              <p className="helper-text">
                Backend enforcement is active. The case request is rejected if this remains unchecked.
              </p>
            </section>
          </div>

          <section className="subpanel">
            <div className="section-header compact">
              <h3>Flight itinerary & flight details</h3>
              <button
                type="button"
                className="secondary-button"
                onClick={addConnectingFlight}
                disabled={flightSegments.length >= 5}
              >
                Add connecting flight
              </button>
            </div>
            <div className="flight-grid">
              {flightSegments.map((segment, index) => (
                <article className="flight-card" key={segment.sequence_number}>
                  <div className="flight-card-header">
                    <h4>{index === 0 ? 'Main flight' : `Connection ${index}`}</h4>
                    {index > 0 ? (
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => removeFlight(index)}
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
                  <label>
                    Departure airport code
                    <input
                      type="text"
                      maxLength="3"
                      value={segment.departure_airport_code}
                      onChange={(event) =>
                        updateFlightSegment(index, 'departure_airport_code', event.target.value.toUpperCase())
                      }
                      required
                    />
                  </label>
                  <label>
                    Arrival airport code
                    <input
                      type="text"
                      maxLength="3"
                      value={segment.arrival_airport_code}
                      onChange={(event) =>
                        updateFlightSegment(index, 'arrival_airport_code', event.target.value.toUpperCase())
                      }
                      required
                    />
                  </label>
                  <label>
                    Flight number
                    <input
                      type="text"
                      value={segment.flight_number}
                      onChange={(event) => updateFlightSegment(index, 'flight_number', event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Flight date
                    <input
                      type="date"
                      value={segment.flight_date}
                      onChange={(event) => updateFlightSegment(index, 'flight_date', event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Airline
                    <input
                      type="text"
                      value={segment.airline}
                      onChange={(event) => updateFlightSegment(index, 'airline', event.target.value)}
                      required
                    />
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="radio"
                      name="problem-flight"
                      checked={segment.is_problem_flight}
                      onChange={() => markProblemFlight(index)}
                    />
                    Mark this as the problem flight
                  </label>
                </article>
              ))}
            </div>
          </section>

          <section className="subpanel compensation-panel">
            <div className="section-header compact">
              <div>
                <h3>CASE_02 compensation preview</h3>
                <p className="helper-text">
                  Calculated from the first departure and final destination only. Connecting-flight
                  legs are not included in the orthodromic distance calculation.
                </p>
              </div>
              <span className="status-pill neutral-pill">
                {compensationPreview.busy ? 'Recalculating...' : 'Auto recalculation active'}
              </span>
            </div>
            <div className="preview-grid">
              <article className="preview-card">
                <span className="callout-label">Distance</span>
                <strong>
                  {compensationPreview.data?.orthodromic_distance_km
                    ? `${compensationPreview.data.orthodromic_distance_km} km`
                    : 'Waiting for valid airports'}
                </strong>
                <small>
                  Route: {(compensationPreview.data?.departure_airport_code ?? departureAirportCode) || '---'} to{' '}
                  {(compensationPreview.data?.arrival_airport_code ?? arrivalAirportCode) || '---'}
                </small>
              </article>
              <article className="preview-card highlight-card">
                <span className="callout-label">Compensation</span>
                <strong>
                  {compensationPreview.data?.compensation_amount_eur
                    ? `€${compensationPreview.data.compensation_amount_eur}`
                    : 'Not available yet'}
                </strong>
                <small>Thresholds: under 1500 km = €250, up to 3500 km = €400, above = €600.</small>
              </article>
            </div>
            {compensationPreview.error ? <p className="feedback error">{compensationPreview.error}</p> : null}
          </section>

          <section className="subpanel disruption-panel">
            <div className="section-header compact">
              <div>
                <h3>CASE_03 disruption details</h3>
                <p className="helper-text">
                  Tell us what type of disruption happened and add a short incident summary so the
                  case can be assessed accurately.
                </p>
              </div>
              <span className="status-pill neutral-pill">Frontend completion enforced</span>
            </div>

            <div className="form-section-grid disruption-grid">
              <label>
                Type of disruption
                <select
                  value={disruptionDetails.disruption_type}
                  onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                    ...current,
                    disruption_type: event.target.value,
                  }))}
                  required
                >
                  <option value="">Select disruption type</option>
                  <option value="CANCELLATION">Cancellation</option>
                  <option value="DELAY">Delay</option>
                  <option value="DENIED_BOARDING">Denied boarding</option>
                </select>
              </label>

              {disruptionDetails.disruption_type === 'CANCELLATION' ? (
                <label>
                  How many days before cancellation has the airline informed?
                  <select
                    value={disruptionDetails.cancellation_notice_timing}
                    onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                      ...current,
                      cancellation_notice_timing: event.target.value,
                    }))}
                    required
                  >
                    <option value="">Select notice timing</option>
                    <option value=">14_DAYS">More than 14 days</option>
                    <option value="<14_DAYS">Less than 14 days</option>
                    <option value="FLIGHT_DAY">On flight day</option>
                  </select>
                </label>
              ) : null}

              {disruptionDetails.disruption_type === 'DELAY' ? (
                <label>
                  How late arrived to final destination?
                  <select
                    value={disruptionDetails.delay_arrival_timing}
                    onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                      ...current,
                      delay_arrival_timing: event.target.value,
                    }))}
                    required
                  >
                    <option value="">Select arrival delay</option>
                    <option value="<3H">Less than 3 hours</option>
                    <option value=">3H">More than 3 hours</option>
                    <option value="CONNECTION_LOST">Connection flight lost</option>
                  </select>
                </label>
              ) : null}

              {disruptionDetails.disruption_type === 'DENIED_BOARDING' ? (
                <>
                  <label>
                    Did you give up your seat voluntarily?
                    <select
                      value={disruptionDetails.denied_boarding_voluntary}
                      onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                        ...current,
                        denied_boarding_voluntary: event.target.value,
                      }))}
                      required
                    >
                      <option value="">Select answer</option>
                      <option value="YES">Yes</option>
                      <option value="NO">No</option>
                    </select>
                  </label>

                  {disruptionDetails.denied_boarding_voluntary === 'NO' ? (
                    <label>
                      Reason behind denial of boarding
                      <select
                        value={disruptionDetails.denied_boarding_reason}
                        onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                          ...current,
                          denied_boarding_reason: event.target.value,
                        }))}
                        required
                      >
                        <option value="">Select reason</option>
                        <option value="FLIGHT_OVERBOOKED">Flight overbooked</option>
                        <option value="AGGRESSIVE_BEHAVIOR">Aggressive behavior with staff</option>
                        <option value="INTOXICATION">Intoxication</option>
                        <option value="UNSPECIFIED_REASON">Unspecified reason</option>
                      </select>
                    </label>
                  ) : null}
                </>
              ) : null}

              {showsAirlineMotiveFields(disruptionDetails.disruption_type) ? (
                <>
                  <label>
                    Did the airline mention disruption motive?
                    <select
                      value={disruptionDetails.airline_motive_known}
                      onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                        ...current,
                        airline_motive_known: event.target.value,
                      }))}
                      required
                    >
                      <option value="">Select answer</option>
                      <option value="YES">Yes</option>
                      <option value="NO">No</option>
                      <option value="UNKNOWN">I don't know</option>
                    </select>
                  </label>

                  {disruptionDetails.airline_motive_known === 'YES' ? (
                    <label>
                      What was the motive communicated by the airline?
                      <select
                        value={disruptionDetails.airline_motive_details}
                        onChange={(event) => setDisruptionDetails((current) => sanitizeDisruptionDetails({
                          ...current,
                          airline_motive_details: event.target.value,
                        }))}
                        required
                      >
                        <option value="">Select motive</option>
                        <option value="TECHNICAL_PROBLEM">Technical problem</option>
                        <option value="METEOROLOGICAL_CONDITIONS">Meteorological conditions</option>
                        <option value="STRIKE">Strike</option>
                        <option value="AIRPORT_PROBLEMS">Problems with airport</option>
                        <option value="CREW_PROBLEMS">Crew problems</option>
                        <option value="OTHER_MOTIVES">Other motives</option>
                      </select>
                    </label>
                  ) : null}
                </>
              ) : null}
            </div>

            <label>
              Describe in short what has happened
              <textarea
                value={disruptionDetails.incident_description}
                onChange={(event) => setDisruptionDetails((current) => ({
                  ...current,
                  incident_description: event.target.value,
                }))}
                rows="6"
                maxLength="4000"
                placeholder="Add the sequence of events, what the airline communicated, and how the disruption affected your journey."
                required
              />
            </label>
            <p className="helper-text character-count">
              {disruptionDetails.incident_description.length}/4000 characters
            </p>
          </section>

          <div className="form-section-grid">
            <section className="subpanel">
              <h3>Required documents</h3>
              <label>
                Boarding pass (PDF/JPG, max 5 MB)
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg"
                  onChange={(event) =>
                    setDocuments({ ...documents, boardingPass: event.target.files?.[0] ?? null })
                  }
                  required
                />
              </label>
              <label>
                ID or passport (PDF/JPG, max 5 MB)
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg"
                  onChange={(event) =>
                    setDocuments({ ...documents, idDocument: event.target.files?.[0] ?? null })
                  }
                  required
                />
              </label>
            </section>

            <section className="subpanel">
              <h3>Airport lookup helper</h3>
              <div className="form-stack">
                <label>
                  Search by IATA code, airport, city, or country
                  <input
                    type="text"
                    value={airportQuery}
                    onChange={(event) => setAirportQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        handleAirportLookup(event)
                      }
                    }}
                    placeholder="OTP, Bucharest, Romania"
                  />
                </label>
                <button type="button" disabled={airportState.busy} onClick={handleAirportLookup}>
                  {airportState.busy ? 'Searching...' : 'Search airports'}
                </button>
                {airportState.error ? <p className="feedback error">{airportState.error}</p> : null}
              </div>
              <ul className="airport-results">
                {airportResults.map((airport) => (
                  <li key={`${airport.code}-${airport.name}`}>
                    <strong>{airport.code}</strong>
                    <span>{airport.name}</span>
                    <small>
                      {airport.city ? `${airport.city}, ` : ''}
                      {airport.country ?? 'Country unavailable'}
                    </small>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <div className="form-actions">
            <button type="submit" disabled={submitState.busy}>
              {submitState.busy ? 'Submitting case...' : 'Submit CASE_01, CASE_02, and CASE_03'}
            </button>
            {submitState.error ? <p className="feedback error">{submitState.error}</p> : null}
            {submitState.success ? <p className="feedback success">{submitState.success}</p> : null}
          </div>
        </form>
      </section>
    </main>
  )
}

function defaultPassenger(user) {
  return {
    email: user?.email ?? '',
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    gdpr_consent: false,
  }
}

function createFlightSegment(sequenceNumber, isProblemFlight) {
  return {
    sequence_number: sequenceNumber,
    departure_airport_code: '',
    arrival_airport_code: '',
    flight_number: '',
    flight_date: '',
    airline: '',
    is_problem_flight: isProblemFlight,
  }
}

function defaultDisruptionDetails() {
  return {
    disruption_type: '',
    cancellation_notice_timing: '',
    delay_arrival_timing: '',
    denied_boarding_voluntary: '',
    denied_boarding_reason: '',
    airline_motive_known: '',
    airline_motive_details: '',
    incident_description: '',
  }
}

function showsAirlineMotiveFields(disruptionType) {
  return disruptionType === 'CANCELLATION' || disruptionType === 'DELAY'
}

function sanitizeDisruptionDetails(details) {
  const nextDetails = { ...details }

  if (nextDetails.disruption_type !== 'CANCELLATION') {
    nextDetails.cancellation_notice_timing = ''
  }
  if (nextDetails.disruption_type !== 'DELAY') {
    nextDetails.delay_arrival_timing = ''
  }
  if (nextDetails.disruption_type !== 'DENIED_BOARDING') {
    nextDetails.denied_boarding_voluntary = ''
    nextDetails.denied_boarding_reason = ''
  }
  if (nextDetails.denied_boarding_voluntary !== 'NO') {
    nextDetails.denied_boarding_reason = ''
  }
  if (!showsAirlineMotiveFields(nextDetails.disruption_type)) {
    nextDetails.airline_motive_known = ''
    nextDetails.airline_motive_details = ''
  }
  if (nextDetails.airline_motive_known !== 'YES') {
    nextDetails.airline_motive_details = ''
  }

  return nextDetails
}

function getDisruptionValidationError(disruptionDetails) {
  if (!disruptionDetails.disruption_type) {
    return 'Please select the type of disruption.'
  }
  if (disruptionDetails.disruption_type === 'CANCELLATION' && !disruptionDetails.cancellation_notice_timing) {
    return 'Please specify when the airline informed you about the cancellation.'
  }
  if (disruptionDetails.disruption_type === 'DELAY' && !disruptionDetails.delay_arrival_timing) {
    return 'Please specify how late you arrived at the final destination.'
  }
  if (disruptionDetails.disruption_type === 'DENIED_BOARDING' && !disruptionDetails.denied_boarding_voluntary) {
    return 'Please specify whether you gave up your seat voluntarily.'
  }
  if (
    disruptionDetails.disruption_type === 'DENIED_BOARDING' &&
    disruptionDetails.denied_boarding_voluntary === 'NO' &&
    !disruptionDetails.denied_boarding_reason
  ) {
    return 'Please specify the reason behind the denied boarding.'
  }
  if (showsAirlineMotiveFields(disruptionDetails.disruption_type) && !disruptionDetails.airline_motive_known) {
    return 'Please specify whether the airline mentioned a disruption motive.'
  }
  if (disruptionDetails.airline_motive_known === 'YES' && !disruptionDetails.airline_motive_details) {
    return 'Please specify the motive communicated by the airline.'
  }
  if (!disruptionDetails.incident_description.trim()) {
    return 'Please describe what happened during the disruption.'
  }

  return ''
}

function App() {
  return <AppShell />
}

export default App
