import React, { useEffect, useState } from 'react'
import axios from 'axios'

const transportTypes = ['bus', 'train', 'flight']
const promoCodeOptions = ['SAVE5', 'SAVE10', 'SAVE15', 'WELCOME5', 'LOYAL10']
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const defaultTripForm = {
  source: 'Bengaluru',
  destination: 'Hyderabad',
  date: 'tomorrow',
  transport: 'bus'
}

const getFareNumber = (fare) => Number(String(fare ?? '').replace(/[^0-9.]/g, '')) || 0

const getWeekendMultiplier = (travelDate, transportType) => {
  const normalizedDate = String(travelDate || '').trim()
  if (!normalizedDate) return 1

  const dateValue = new Date(normalizedDate)
  if (Number.isNaN(dateValue.getTime())) return 1

  const isWeekend = [0, 6].includes(dateValue.getDay())
  if (!isWeekend) return 1

  return transportType === 'flight' ? 1.08 : 1.12
}

const getSeatClassMultiplier = (seatClass) => {
  const value = String(seatClass || 'economy').toLowerCase()
  const factors = {
    economy: 1,
    standard: 1,
    premium: 1.22,
    business: 1.48,
    first: 1.8,
  }

  return factors[value] || 1
}

const getDiscountMultiplier = (discountCode, loyaltyPoints) => {
  const code = String(discountCode || '').trim().toUpperCase()
  let discountRate = 0

  if (['SAVE5', 'WELCOME5'].includes(code)) discountRate += 0.05
  else if (['SAVE10', 'LOYAL10', 'TRAVEL10'].includes(code)) discountRate += 0.10
  else if (['SAVE15', 'VIP15', 'TRAVEL15'].includes(code)) discountRate += 0.15
  else if (['SAVE20', 'PLUS20'].includes(code)) discountRate += 0.20

  discountRate += Math.min(Number(loyaltyPoints || 0) / 1000, 0.2)
  return 1 - Math.min(discountRate, 0.55)
}

const calculateDynamicFare = (baseFare, transportType, departTime, travelDate, seatClass, discountCode, loyaltyPoints) => {
  const weekendMultiplier = getWeekendMultiplier(travelDate, transportType)
  const seatClassMultiplier = getSeatClassMultiplier(seatClass)
  const discountMultiplier = getDiscountMultiplier(discountCode, loyaltyPoints)

  return Number((Number(baseFare || 0) * weekendMultiplier * seatClassMultiplier * discountMultiplier).toFixed(2))
}

function App() {
  const [messages, setMessages] = useState([
    { from: 'bot', text: 'Hi, I am TravelMate AI. Tell me your route and I will help you book a ticket.' }
  ])
  const [input, setInput] = useState('')
  const [tripForm, setTripForm] = useState(defaultTripForm)
  const [availableOptions, setAvailableOptions] = useState([])
  const [selectedAgency, setSelectedAgency] = useState('all')
  const [sortMode, setSortMode] = useState('earliest')
  const [selectedOption, setSelectedOption] = useState(null)
  const [selectedSeats, setSelectedSeats] = useState(1)
  const [bookings, setBookings] = useState([])
  const [currentBookingId, setCurrentBookingId] = useState('')
  const [bookingStatus, setBookingStatus] = useState('Not booked yet')
  const [ticket, setTicket] = useState(null)
  const [activeTab, setActiveTab] = useState('Booking')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [step, setStep] = useState('search')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedSeatNumbers, setSelectedSeatNumbers] = useState(['A1'])
  const [seatPopup, setSeatPopup] = useState(null)
  const [seatClass, setSeatClass] = useState('economy')
  const [discountCode, setDiscountCode] = useState('SAVE10')
  const [loyaltyPoints, setLoyaltyPoints] = useState(100)

  const getSeatLayout = (transportType = tripForm.transport) => {
    const transport = String(transportType || 'bus').toLowerCase()

    if (transport === 'flight') {
      return Array.from({ length: 12 }, (_, rowIndex) => {
        const rowLabel = String.fromCharCode(65 + rowIndex)
        const seats = [
          { id: `${rowLabel}1`, label: '1', available: rowIndex % 3 !== 0 },
          { id: `${rowLabel}2`, label: '2', available: rowIndex % 4 !== 0 },
          { id: `${rowLabel}3`, label: '3', available: rowIndex % 2 !== 0 },
          { id: `${rowLabel}4`, label: '4', available: rowIndex % 5 !== 0 },
          { id: `${rowLabel}5`, label: '5', available: rowIndex % 3 !== 1 },
          { id: `${rowLabel}6`, label: '6', available: rowIndex % 4 !== 1 }
        ]
        return { row: rowLabel, seats }
      })
    }

    if (transport === 'train') {
      return Array.from({ length: 8 }, (_, rowIndex) => {
        const rowLabel = String.fromCharCode(65 + rowIndex)
        const seats = [
          { id: `${rowLabel}1`, label: 'L1', available: rowIndex % 2 !== 0 },
          { id: `${rowLabel}2`, label: 'L2', available: rowIndex % 3 !== 0 },
          { id: `${rowLabel}3`, label: 'R1', available: rowIndex % 4 !== 0 },
          { id: `${rowLabel}4`, label: 'R2', available: rowIndex % 5 !== 0 }
        ]
        return { row: rowLabel, seats }
      })
    }

    return Array.from({ length: 6 }, (_, rowIndex) => {
      const rowLabel = String.fromCharCode(65 + rowIndex)
      const seats = [
        { id: `${rowLabel}1`, label: '1', available: rowIndex % 2 !== 0 },
        { id: `${rowLabel}2`, label: '2', available: rowIndex % 3 !== 0 },
        { id: `${rowLabel}3`, label: '3', available: rowIndex % 4 !== 0 },
        { id: `${rowLabel}4`, label: '4', available: rowIndex % 5 !== 0 }
      ]
      return { row: rowLabel, seats }
    })
  }

  const seatLayout = getSeatLayout(selectedOption?.transport || tripForm.transport)

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/booking/history`)
      setBookings(res.data || [])
    } catch (error) {
      setBookings([])
    }
  }

  const clearHistory = async () => {
    try {
      await axios.delete(`${API_BASE_URL}/booking/history`)
      setBookings([])
      setMessages((prev) => [...prev, { from: 'bot', text: 'Booking history cleared.' }])
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'Could not clear the history right now.' }])
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(() => {
    if (activeTab === 'History') {
      loadHistory()
    }
  }, [activeTab])

  useEffect(() => {
    if (!selectedOption) {
      setSelectedSeatNumbers(['A1'])
      setSelectedSeats(1)
      return
    }

    setSelectedSeatNumbers([`${String.fromCharCode(65 + (selectedOption.id.length % 6))}1`])
    setSelectedSeats(1)
  }, [selectedOption?.id])

  const searchTrips = async () => {
    const { source, destination, date, transport } = tripForm
    if (!source || !destination) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'Please enter both the departure city and destination city.' }])
      return
    }

    setIsLoading(true)
    try {
      const res = await axios.get(`${API_BASE_URL}/transport/search`, {
        params: { source, destination, date: date || 'tomorrow', transport }
      })
      const options = res.data || []
      setAvailableOptions(options)
      setSelectedAgency('all')

      if (options.length === 0) {
        setSelectedOption(null)
        setStep('search')
        setMessages((prev) => [...prev, { from: 'bot', text: 'No trips found for that route and transport. Please try another option.' }])
        return
      }

      setSelectedOption(options[0])
      setStep('choose')
      setMessages((prev) => [...prev, { from: 'bot', text: `I found ${options.length} ${transport} options for ${source} to ${destination}. Please choose your preferred travel agency.` }])
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'I could not fetch transport options right now. Please try again.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickPrompt = async (promptText) => {
    const text = promptText.toLowerCase()
    const fromMatch = text.match(/from\s+([a-z]+(?:\s+[a-z]+)*)/i)
    const toMatch = text.match(/to\s+([a-z]+(?:\s+[a-z]+)*)/i)
    const transportMatch = transportTypes.find((type) => text.includes(type))
    const dateMatch = text.includes('tomorrow') ? 'tomorrow' : text.includes('monday') ? 'next monday' : 'tomorrow'

    setTripForm((prev) => ({
      ...prev,
      source: fromMatch ? fromMatch[1].trim() : prev.source,
      destination: toMatch ? toMatch[1].trim() : prev.destination,
      transport: transportMatch || prev.transport,
      date: dateMatch
    }))

    setInput('')
    setMessages((prev) => [...prev, { from: 'user', text: promptText }])
    setStep('search')

    const source = fromMatch ? fromMatch[1].trim() : defaultTripForm.source
    const destination = toMatch ? toMatch[1].trim() : defaultTripForm.destination
    const transport = transportMatch || defaultTripForm.transport

    setIsLoading(true)
    try {
      const res = await axios.get(`${API_BASE_URL}/transport/search`, {
        params: { source, destination, date: dateMatch, transport }
      })
      const options = res.data || []
      setAvailableOptions(options)
      setSelectedAgency('all')
      setSelectedOption(options[0] || null)
      setStep(options.length > 0 ? 'choose' : 'search')
      setMessages((prev) => [...prev, { from: 'bot', text: options.length > 0 ? `I found ${options.length} ${transport} options for ${source} to ${destination}.` : 'No trips were found for that route.' }])
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'I could not fetch the trip options. Please try another request.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const send = async (overrideText) => {
    const value = (overrideText ?? input).trim()
    if (!value) return

    const userMsg = { from: 'user', text: value }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const res = await axios.post(`${API_BASE_URL}/chat/message`, { message: value })
      const botReply = res.data.reply || 'I can help with that.'
      setMessages((prev) => [...prev, { from: 'bot', text: botReply }])

      const context = res.data.context || {}
      if (context.source || context.destination || context.transport || context.date) {
        setTripForm((prev) => ({
          source: context.source || prev.source,
          destination: context.destination || prev.destination,
          date: context.date || prev.date,
          transport: context.transport || prev.transport
        }))
      }

      if (context.source && context.destination && context.transport && context.date) {
        await searchTrips()
      }
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'The backend is unavailable right now. Please try again in a moment.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const agencyOptions = Array.from(new Set((availableOptions || []).map((option) => option.provider)))
  const parseTime = (timeText) => {
    const [h, m] = String(timeText || '00:00').split(':').map(Number)
    return (h || 0) * 60 + (m || 0)
  }

  const orderedOptions = [...(availableOptions || [])].sort((a, b) => {
    if (sortMode === 'cheapest') return getFareNumber(a.fare) - getFareNumber(b.fare)
    if (sortMode === 'fastest') return (parseTime(a.arrive_time) - parseTime(a.depart_time)) - (parseTime(b.arrive_time) - parseTime(b.depart_time))
    return parseTime(a.depart_time) - parseTime(b.depart_time)
  })

  const filteredOptions = selectedAgency === 'all'
    ? orderedOptions
    : orderedOptions.filter((option) => option.provider === selectedAgency)

  const updatePassengerCount = (delta) => {
    setSelectedSeats((prev) => {
      const nextValue = Math.max(1, Math.min(6, prev + delta))
      const nextSelections = []
      const layout = getSeatLayout(selectedOption?.transport || tripForm.transport)
      const allSeats = layout.flatMap((row) => row.seats.filter((seat) => seat.available).map((seat) => seat.id))

      for (let i = 0; i < nextValue; i += 1) {
        const seatId = allSeats[i] || 'A1'
        if (!nextSelections.includes(seatId)) {
          nextSelections.push(seatId)
        }
      }

      setSelectedSeatNumbers(nextSelections)
      return nextValue
    })
  }

  const baseFare = getFareNumber(selectedOption?.fare)
  const weekendMultiplier = getWeekendMultiplier(tripForm.date, selectedOption?.transport)
  const seatClassMultiplier = getSeatClassMultiplier(seatClass)
  const discountMultiplier = getDiscountMultiplier(discountCode, loyaltyPoints)

  const effectiveSingleFare = selectedOption
    ? calculateDynamicFare(
        selectedOption.fare,
        selectedOption.transport,
        selectedOption.depart_time,
        tripForm.date,
        seatClass,
        discountCode,
        loyaltyPoints,
      )
    : 0

  const totalAmount = effectiveSingleFare * selectedSeats
  const fareBreakdown = {
    baseFare,
    weekendSurcharge: Number((baseFare * (weekendMultiplier - 1)).toFixed(2)),
    seatClassSurcharge: Number((baseFare * (seatClassMultiplier - 1)).toFixed(2)),
    discountAmount: Number((baseFare * (1 - discountMultiplier)).toFixed(2)),
    loyaltyBenefit: Number((baseFare * Math.min(Number(loyaltyPoints || 0) / 1000, 0.2)).toFixed(2)),
    finalFare: effectiveSingleFare,
  }

  useEffect(() => {
    if (!seatPopup) return undefined

    const timer = setTimeout(() => {
      setSeatPopup(null)
    }, 1400)

    return () => clearTimeout(timer)
  }, [seatPopup])

  const handleSeatToggle = (seatId) => {
    const isSelected = selectedSeatNumbers.includes(seatId)

    if (isSelected) {
      const nextSelection = selectedSeatNumbers.filter((seat) => seat !== seatId)
      setSelectedSeatNumbers(nextSelection)
      setSelectedSeats(Math.max(1, nextSelection.length || 1))
      setSeatPopup({ seatId, action: 'removed' })
      return
    }

    if (selectedSeatNumbers.length >= 6) {
      return
    }

    const nextSelection = [...selectedSeatNumbers, seatId]
    setSelectedSeatNumbers(nextSelection)
    setSelectedSeats(nextSelection.length)
    setSeatPopup({ seatId, action: 'selected' })
  }

  const handleBookSelected = async () => {
    if (!selectedOption) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'Please choose a transport option before booking.' }])
      return
    }

    try {
      const create = await axios.post(`${API_BASE_URL}/booking/create`, {
        user_id: 'demo',
        transport_id: selectedOption.id,
        seats: selectedSeats,
        source: tripForm.source,
        destination: tripForm.destination,
        date: tripForm.date,
        provider: selectedOption.provider,
        amount: totalAmount,
        transport_type: selectedOption.transport,
        seat_class: seatClass,
        discount_code: discountCode || null,
        loyalty_points: loyaltyPoints,
      })
      const bookingId = create.data.booking_id
      setCurrentBookingId(bookingId)
      setBookingStatus(create.data.status)
      setTicket(null)
      setStep('payment')
      setMessages((prev) => [...prev, { from: 'bot', text: `Booking created for ${selectedOption.provider}. Booking ID: ${bookingId}. Please proceed to payment.` }])
      await loadHistory()
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'Booking failed. Please try another option.' }])
    }
  }

  const handlePayNow = async () => {
    if (!currentBookingId) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'There is no active booking to pay for yet.' }])
      return
    }

    try {
      const pay = await axios.post(`${API_BASE_URL}/booking/pay/${currentBookingId}`)
      setBookingStatus(pay.data.status)
      setTicket({
        bookingId: currentBookingId,
        provider: selectedOption.provider,
        route: `${tripForm.source} → ${tripForm.destination}`,
        departure: tripForm.date,
        seats: selectedSeats,
        amount: totalAmount,
        status: pay.data.status,
        qrUrl: `${API_BASE_URL}/booking/ticket-qr/${currentBookingId}`,
      })
      setMessages((prev) => [...prev, { from: 'bot', text: `Payment confirmed for booking ${currentBookingId}. Your ticket is ready.` }])
      await loadHistory()
    } catch (error) {
      setMessages((prev) => [...prev, { from: 'bot', text: 'Payment could not be completed. Please try again.' }])
    }
  }

  return (
    <div className="page-shell">
      {!sidebarCollapsed && (
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">✈</div>
            <div>
              <div className="brand-title">TravelMate</div>
              <div className="brand-subtitle">AI trip assistant</div>
            </div>
          </div>

          <nav className="nav">
            {['Booking', 'History', 'Payments', 'Support'].map((tab) => (
              <button
                key={tab}
                className={`nav-item ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>

          <div className="sidebar-card">
            <p className="eyebrow">Today</p>
            <h3>2 trips planned</h3>
            <span>3 tickets confirmed</span>
          </div>
        </aside>
      )}

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <button className="sidebar-toggle" onClick={() => setSidebarCollapsed((prev) => !prev)}>
              {sidebarCollapsed ? '☰' : '✕'}
            </button>
            <div>
              <p className="eyebrow">Smart booking</p>
              <h1>TravelMate AI – Intelligent Ticket Booking Assistant</h1>
            </div>
          </div>
          <div className="status-pill">Online</div>
        </header>

        <div className="content-grid">
          <section className="chat-panel">
            <div className="chat-list">
              {messages.map((message, index) => (
                <div key={index} className={`msg ${message.from}`}>
                  {message.text}
                </div>
              ))}
              {isLoading && <div className="msg bot typing">Thinking...</div>}
            </div>

            <div className="composer">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your travel request..."
                onKeyDown={(e) => e.key === 'Enter' && send()}
              />
              <button onClick={() => send()}>Send</button>
            </div>
          </section>

          <aside className="info-panel">
            {activeTab === 'History' ? (
              <div className="history-panel">
                <div className="panel-header">
                  <p className="eyebrow">Booking history</p>
                  <h3>Recent trips</h3>
                </div>

                <button className="clear-history-btn" onClick={clearHistory}>
                  Clear History
                </button>

                <div className="history-list">
                  {bookings.length === 0 ? (
                    <div className="history-empty">No bookings yet.</div>
                  ) : (
                    bookings.map((booking) => {
                      const from = booking.source || 'Unknown'
                      const to = booking.destination || 'Unknown'
                      const route = `${from} → ${to}`
                      const provider = booking.provider || booking.transport_id || 'Travel option'
                      const amount = Number(booking.amount ?? 0) || 0
                      const bookingDate = booking.date || booking.created_at || '—'

                      return (
                        <div key={booking.booking_id} className="history-item">
                          <div className="history-main">
                            <div className="history-header-row">
                              <strong>{route}</strong>
                              <span className={`tag ${booking.status}`}>{booking.status}</span>
                            </div>
                            <div className="history-meta">Paid Amount: ₹{amount.toLocaleString()}</div>
                            <div className="history-meta">Provider: {provider}</div>
                            <div className="history-meta">From: {from} • To: {to}</div>
                            <div className="history-meta">Date: {bookingDate}</div>
                            <div className="history-meta">Seats: {booking.seats}</div>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            ) : (
              <div className="booking-wizard">
                <div className="wizard-header">
                  <p className="eyebrow">Travel booking</p>
                  <h3>Plan your trip</h3>
                </div>

                <div className="field-grid">
                  <label className="field">
                    <span>From</span>
                    <input
                      value={tripForm.source}
                      onChange={(e) => setTripForm((prev) => ({ ...prev, source: e.target.value }))}
                    />
                  </label>

                  <label className="field">
                    <span>To</span>
                    <input
                      value={tripForm.destination}
                      onChange={(e) => setTripForm((prev) => ({ ...prev, destination: e.target.value }))}
                    />
                  </label>

                  <label className="field">
                    <span>Date</span>
                    <input
                      type="date"
                      value={tripForm.date === 'tomorrow' || tripForm.date === 'next monday' ? '' : tripForm.date}
                      onChange={(e) => setTripForm((prev) => ({ ...prev, date: e.target.value }))}
                    />
                  </label>

                  <label className="field">
                    <span>Transport</span>
                    <select
                      value={tripForm.transport}
                      onChange={(e) => setTripForm((prev) => ({ ...prev, transport: e.target.value }))}
                    >
                      {transportTypes.map((type) => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <button className="search-btn" onClick={searchTrips}>
                  Search trips
                </button>

                {step !== 'search' && availableOptions.length > 0 && (
                  <div className="option-list">
                    <div className="route-map-card">
                      <div className="route-map-header">
                        <span className="route-map-chip">Route overview</span>
                        <span>{tripForm.date}</span>
                      </div>
                      <div className="route-map-body">
                        <div className="route-stop">
                          <span className="route-dot route-dot-start" />
                          <div>
                            <small>From</small>
                            <strong>{tripForm.source}</strong>
                          </div>
                        </div>
                        <div className="route-line" />
                        <div className="route-stop">
                          <span className="route-dot route-dot-end" />
                          <div>
                            <small>To</small>
                            <strong>{tripForm.destination}</strong>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="section-label">Travel agency</div>
                    <select
                      className="agency-select"
                      value={selectedAgency}
                      onChange={(event) => setSelectedAgency(event.target.value)}
                    >
                      <option value="all">All agencies</option>
                      {agencyOptions.map((agency) => (
                        <option key={agency} value={agency}>{agency}</option>
                      ))}
                    </select>

                    <div className="section-label">Sort by</div>
                    <select
                      className="agency-select"
                      value={sortMode}
                      onChange={(event) => setSortMode(event.target.value)}
                    >
                      <option value="earliest">Earliest departure</option>
                      <option value="cheapest">Cheapest fare</option>
                      <option value="fastest">Fastest journey</option>
                    </select>

                    <div className="section-label">Available options</div>
                    {filteredOptions.map((option) => (
                      <button
                        key={option.id}
                        className={`option-card ${selectedOption?.id === option.id ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedOption(option)
                          setStep('payment')
                        }}
                      >
                        <div className="option-topline">
                          <strong>{option.provider}</strong>
                          <span>{option.transport.toUpperCase()}</span>
                        </div>
                        <div className="option-route">{tripForm.source} → {tripForm.destination}</div>
                        <div className="option-meta">
                          <span>{option.depart_time} departure</span>
                          <span>{option.seats_available} seats left</span>
                        </div>
                        <div className="option-price">₹{option.fare}</div>
                      </button>
                    ))}
                  </div>
                )}

                {selectedOption && (
                  <div className="payment-box">
                    <div className="seat-selection-panel">
                      <div className="seat-selection-left">
                        {seatPopup && (
                          <div className="seat-popup-card">
                            <div className="seat-popup-header">
                              <span className="seat-popup-badge">Seat</span>
                              <span className={`seat-popup-status ${seatPopup.action === 'selected' ? 'ok' : 'warn'}`} />
                            </div>
                            <span className="seat-popup-label">{seatPopup.action === 'selected' ? 'Selected' : 'Removed'}</span>
                            <strong>{seatPopup.seatId}</strong>
                          </div>
                        )}

                        <div className="section-label">Select Seats</div>
                        <div className="seat-map-header-row">
                          <span className="seat-map-title">{selectedOption.transport.toUpperCase()} SEAT MAP</span>
                          <span className="seat-map-status">{selectedSeatNumbers.length} selected</span>
                        </div>

                        <div className="seat-map-legend">
                          <span><i className="legend-dot available" /> Available</span>
                          <span><i className="legend-dot selected" /> Selected</span>
                          <span><i className="legend-dot unavailable" /> Unavailable</span>
                        </div>

                        <div className="seat-map-wrap">
                          <div className="seat-map-grid">
                            {seatLayout.map((row) => (
                              <div key={row.row} className="seat-row-group">
                                <span className="seat-row-label">{row.row}</span>
                                <div className="seat-row-cells">
                                  {row.seats.map((seat) => {
                                    const isSelected = selectedSeatNumbers.includes(seat.id)
                                    const isDisabled = !seat.available

                                    return (
                                      <button
                                        key={seat.id}
                                        type="button"
                                        className={`seat-button ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                                        onClick={() => !isDisabled && handleSeatToggle(seat.id)}
                                        disabled={isDisabled}
                                        title={`Seat ${seat.id}`}
                                      >
                                        {seat.label}
                                      </button>
                                    )
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="section-label">Seat selection</div>
                    <div className="seat-row">
                      <span>Passengers</span>
                      <div className="passenger-control">
                        <button type="button" onClick={() => updatePassengerCount(-1)}>-</button>
                        <strong>{selectedSeats}</strong>
                        <button type="button" onClick={() => updatePassengerCount(1)}>+</button>
                      </div>
                    </div>

                    <div className="field-grid compact-fields">
                      <label className="field">
                        <span>Seat class</span>
                        <select value={seatClass} onChange={(e) => setSeatClass(e.target.value)}>
                          <option value="economy">Economy</option>
                          <option value="premium">Premium</option>
                          <option value="business">Business</option>
                          <option value="first">First</option>
                        </select>
                      </label>

                      <label className="field">
                        <span>Discount code</span>
                        <input
                          value={discountCode}
                          onChange={(e) => setDiscountCode(e.target.value.toUpperCase())}
                          placeholder="SAVE10"
                        />
                      </label>

                      <label className="field">
                        <span>Loyalty points</span>
                        <input
                          type="number"
                          min="0"
                          max="500"
                          value={loyaltyPoints}
                          onChange={(e) => setLoyaltyPoints(Number(e.target.value || 0))}
                        />
                      </label>
                    </div>

                    <div className="promo-chips">
                      {promoCodeOptions.map((code) => (
                        <button
                          key={code}
                          type="button"
                          className={`promo-chip ${discountCode === code ? 'active' : ''}`}
                          onClick={() => setDiscountCode(code)}
                        >
                          {code}
                        </button>
                      ))}
                    </div>

                    <div className="fare-breakdown">
                      <div className="fare-breakdown-header">
                        <span>Fare breakdown</span>
                        <strong>₹{effectiveSingleFare}</strong>
                      </div>
                      <div className="fare-row"><span>Base fare</span><strong>₹{fareBreakdown.baseFare}</strong></div>
                      <div className="fare-row"><span>Weekend surcharge</span><strong>₹{fareBreakdown.weekendSurcharge}</strong></div>
                      <div className="fare-row"><span>Seat class uplift</span><strong>₹{fareBreakdown.seatClassSurcharge}</strong></div>
                      <div className="fare-row"><span>Discount</span><strong>-₹{fareBreakdown.discountAmount}</strong></div>
                      <div className="fare-row"><span>Loyalty benefit</span><strong>-₹{fareBreakdown.loyaltyBenefit}</strong></div>
                    </div>

                    <div className="summary-line">
                      <span>Travel date</span>
                      <strong>{tripForm.date}</strong>
                    </div>
                    <div className="summary-line">
                      <span>Fare per seat</span>
                      <strong>₹{effectiveSingleFare}</strong>
                    </div>
                    <div className="summary-line total">
                      <span>Total</span>
                      <strong>₹{totalAmount}</strong>
                    </div>

                    <button className="primary-btn" onClick={handleBookSelected}>Book now</button>
                    <button className="secondary-btn" onClick={handlePayNow}>Proceed to payment</button>
                    <div className="booking-status">Status: {bookingStatus}</div>

                    {ticket && (
                      <div className="ticket-generated">
                        <div className="section-label">Generated ticket</div>
                        <div className="ticket-card-box">
                          <div className="ticket-topbar">
                            <div>
                              <div className="ticket-brand">TravelMate AI</div>
                              <div className="ticket-title">Boarding Pass</div>
                            </div>
                            <img className="ticket-qr-image" src={ticket.qrUrl} alt="Travel ticket QR code" />
                          </div>

                          <div className="ticket-grid">
                            <div className="ticket-detail">
                              <span>Booking ID</span>
                              <strong>{ticket.bookingId}</strong>
                            </div>
                            <div className="ticket-detail">
                              <span>Status</span>
                              <strong>{ticket.status}</strong>
                            </div>
                            <div className="ticket-detail wide">
                              <span>Route</span>
                              <strong>{ticket.route}</strong>
                            </div>
                            <div className="ticket-detail">
                              <span>Provider</span>
                              <strong>{ticket.provider}</strong>
                            </div>
                            <div className="ticket-detail">
                              <span>Departure</span>
                              <strong>{ticket.departure}</strong>
                            </div>
                            <div className="ticket-detail">
                              <span>Seats</span>
                              <strong>{ticket.seats}</strong>
                            </div>
                          </div>

                          <div className="ticket-invoice">
                            <div className="ticket-invoice-row"><span>Ticket fare</span><strong>₹{ticket.amount}</strong></div>
                            <div className="ticket-invoice-row"><span>Service fee</span><strong>₹0</strong></div>
                            <div className="ticket-invoice-row total"><span>Total paid</span><strong>₹{ticket.amount}</strong></div>
                          </div>
                        </div>
                        <a
                          className="ticket-button"
                          href={`${API_BASE_URL}/booking/ticket/${ticket.bookingId}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Download PDF ticket
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
