import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [error, setError] = useState('')
  const [logs, setLogs] = useState([])
  const [systemHealth, setSystemHealth] = useState(null)
  const logEndRef = useRef(null)

  // 📡 WebSocket & Health Logic (Untouched Original)
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws")
    ws.onmessage = (event) => {
      const time = new Date().toLocaleTimeString()
      setLogs(prevLogs => [`[${time}] ${event.data}`, ...prevLogs])
    }
    return () => ws.close()
  }, [])

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/system/health");
        const data = await res.json();
        setSystemHealth(data);
      } catch (err) { console.error(err); }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 3000);
    return () => clearInterval(interval);
  }, [])

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  // 🔑 Auth Functions
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password })
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem("aws_token", data.access_token);
        setIsLoggedIn(true);
      } else { setError("🚨 Access Denied: Invalid credentials."); }
    } catch (err) { setError("🚨 Server Error."); }
  }

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch("http://localhost:8000/register", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password })
      });
      if (response.ok) { setIsVerifying(true); setError("📩 Code sent!"); }
      else { const data = await response.json(); setError(`🚨 Error: ${data.detail}`); }
    } catch (err) { setError("🚨 Server Error."); }
  }

  const handleVerify = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:8000/verify", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, code: verificationCode })
      });
      if (response.ok) { setIsVerifying(false); setIsRegistering(false); setError("✅ Verified!"); }
      else { setError(`🚨 Invalid code.`); }
    } catch (err) { setError("🚨 Server Error."); }
  }

  // ⚡ THE FIX: This now tells the Python backend to switch you to OFFLINE
  const handleLogout = async () => {
    const token = localStorage.getItem("aws_token");
    try {
      await fetch("http://localhost:8000/logout", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
    } catch (err) {
      console.error("Error communicating with server during logout.");
    }
    localStorage.removeItem("aws_token");
    setIsLoggedIn(false);
    setPassword('');
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#0f172a', color: 'white', fontFamily: 'monospace', overflow: 'hidden' }}>

      {/* 🛡️ SIDEBAR */}
      <div style={{ width: '420px', padding: '30px', borderRight: '1px solid #334155', backgroundColor: '#0b1222', display: 'flex', flexDirection: 'column', gap: '20px' }}>

        <div style={{ textAlign: 'center' }}>
          <h1 style={{ color: '#00ff00', margin: 0, fontSize: '2.4rem' }}>🛡️ RAAMIAS</h1>
          <h3 style={{ color: '#94a3b8', margin: '5px 0 0 0', fontSize: '16px' }}>Command Center</h3>
        </div>

        {/* TELEMETRY */}
        {systemHealth && (
          <div style={{ padding: '20px', backgroundColor: '#0f172a', borderRadius: '10px', border: '1px solid #334155' }}>
            <h4 style={{ margin: '0 0 15px 0', color: '#94a3b8', textAlign: 'center', fontSize: '13px' }}>LIVE SYSTEM TELEMETRY</h4>
            <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
              {systemHealth.user_health.map((user, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: '11px' }}>
                  <span>{user.email}</span>
                  <span style={{ color: user.status.includes('BANNED') ? '#ef4444' : user.status.includes('ONLINE') ? '#16a34a' : '#ffffff', fontWeight: 'bold' }}>
                    {user.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AUTH SECTION */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {!isLoggedIn ? (
            isVerifying ? (
              <form onSubmit={handleVerify} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                <h2 style={{ textAlign: 'center', fontSize: '18px' }}>Verify Identity</h2>
                <input type="text" placeholder="6-Digit Code" value={verificationCode} onChange={(e) => setVerificationCode(e.target.value)} style={{ padding: "12px", borderRadius: "5px", border: "1px solid #475569", backgroundColor: "#1e293b", color: "white", textAlign: 'center' }} required />
                <button type="submit" style={{ padding: "12px", backgroundColor: "#0284c7", color: "white", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>CONFIRM IDENTITY</button>
              </form>
            ) : (
              <form onSubmit={isRegistering ? handleRegister : handleLogin} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                <h2 style={{ textAlign: 'center', margin: '0 0 5px 0', fontSize: '18px' }}>
                  {isRegistering ? "Register New Admin" : "Admin Authentication"}
                </h2>
                <input type="text" placeholder="Admin Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ padding: "12px", borderRadius: "5px", border: "1px solid #475569", backgroundColor: "#1e293b", color: "white" }} required />
                <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ padding: "12px", borderRadius: "5px", border: "1px solid #475569", backgroundColor: "#1e293b", color: "white" }} required />
                <button type="submit" style={{ padding: "12px", backgroundColor: isRegistering ? "#0284c7" : "#16a34a", color: "white", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}>
                  {isRegistering ? "CREATE ACCOUNT" : "INITIALIZE CONNECTION"}
                </button>
                <p onClick={() => { setIsRegistering(!isRegistering); setError(''); }} style={{ textAlign: "center", color: "#38bdf8", cursor: "pointer", fontSize: "13px", textDecoration: "underline" }}>
                  {isRegistering ? "Back to Login" : "Request Access (Sign Up)"}
                </p>
                {error && <p style={{ color: "#ef4444", textAlign: "center", fontSize: '12px', fontWeight: 'bold' }}>{error}</p>}
              </form>
            )
          ) : (
            <div style={{ textAlign: 'center', padding: '30px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #16a34a' }}>
              <div style={{ width: '60px', height: '60px', borderRadius: '50%', backgroundColor: '#16a34a', margin: '0 auto 15px auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px' }}>🧑‍💻</div>
              <h2 style={{ fontSize: '18px' }}>Access Granted</h2>
              <p style={{ color: '#00ff00', fontSize: '12px' }}>🟢 Sentinel Online:<br />{email}</p>
              <button onClick={handleLogout} style={{ padding: "10px", backgroundColor: "#ef4444", color: "white", border: "none", borderRadius: "5px", cursor: "pointer", width: "100%", fontWeight: "bold" }}>DISCONNECT</button>
            </div>
          )}
        </div>
      </div>

      {/* 📡 MAIN PANEL */}
      <div style={{ flex: 1, padding: '40px', display: 'flex', flexDirection: 'column', backgroundColor: '#0b1222' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px', borderBottom: '1px solid #334155', paddingBottom: '15px' }}>
          <h2 style={{ margin: 0 }}>GLOBAL THREAT FEED</h2>
          <span style={{ color: '#00ff00', border: '1px solid #00ff00', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold' }}>● LIVE STREAM</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {logs.map((log, index) => {
            const isCritical = log.includes("BLOCK") || log.includes("BANNED") || log.includes("FAILED");
            const isSuccess = log.includes("SUCCESS") || log.includes("Authorized");
            return (
              <div key={index} style={{ marginBottom: "10px", padding: "15px", backgroundColor: "#0f172a", borderRadius: "8px", borderLeft: isCritical ? "5px solid #ef4444" : isSuccess ? "5px solid #00ff00" : "5px solid #38bdf8" }}>
                <span style={{ fontSize: '14px' }}>{log}</span>
              </div>
            );
          })}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}

export default App