import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isRegistering, setIsRegistering] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [logs, setLogs] = useState([])

  // 🔌 WebSocket Connection: Real-time Threat Feed
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws")
    ws.onmessage = (event) => {
      const time = new Date().toLocaleTimeString()
      setLogs(prevLogs => [`[${time}] ${event.data}`, ...prevLogs])
    }
    return () => ws.close()
  }, [])

  // 🚀 Login Logic (Saves the Token)
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password })
      });

      const data = await response.json();

      if (response.ok) {
        // 💾 STORE TOKEN: This is the "Authorize" step for the frontend
        localStorage.setItem("aws_token", data.access_token);
        setIsLoggedIn(true);
      } else {
        setError("🚨 Access Denied: Invalid credentials.");
      }
    } catch (err) {
      setError("🚨 Server Error: Cannot reach AWS.");
    }
  }

  // 📝 Registration Logic
  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch("http://localhost:8000/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, password: password })
      });
      if (response.ok) {
        setError("✅ Registration successful! You can now log in.");
        setIsRegistering(false);
        setPassword('');
      } else {
        const data = await response.json();
        setError(`🚨 Error: ${data.detail || "Registration failed"}`);
      }
    } catch (err) {
      setError("🚨 Server Error: Cannot reach AWS.");
    }
  }

  // 🛑 Secure Logout (Sends the Token to Python)
  const handleLogout = async () => {
    const token = localStorage.getItem("aws_token");

    try {
      await fetch("http://localhost:8000/logout", {
        method: "POST",
        headers: {
          // 🛡️ Hand the "VIP Pass" to the Python backend
          "Authorization": `Bearer ${token}`
        }
      });
    } catch (err) {
      console.log("Server notified of logout");
    }

    // Clear local state
    localStorage.removeItem("aws_token");
    setIsLoggedIn(false);
    setPassword('');
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#1e293b', color: 'white', fontFamily: 'monospace' }}>

      {/* 🛡️ LEFT SIDE: Command Center */}
      <div style={{ width: '35%', padding: '40px', borderRight: '1px solid #334155', backgroundColor: '#0f172a', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <h1 style={{ color: '#00ff00', textAlign: 'center', marginBottom: '5px' }}>🛡️ RAAMIAS</h1>
        <h3 style={{ textAlign: 'center', color: '#94a3b8', marginBottom: '40px' }}>Command Center</h3>

        {!isLoggedIn ? (
          <form onSubmit={isRegistering ? handleRegister : handleLogin} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
            <h2 style={{ textAlign: 'center', margin: '0 0 10px 0', fontSize: '18px' }}>
              {isRegistering ? "Register New Admin" : "Admin Authentication"}
            </h2>
            <input
              type="email" placeholder="Admin Email" value={email} onChange={(e) => setEmail(e.target.value)}
              style={{ padding: "12px", borderRadius: "5px", border: "1px solid #475569", backgroundColor: "#233046", color: "white" }} required
            />
            <input
              type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)}
              style={{ padding: "12px", borderRadius: "5px", border: "1px solid #475569", backgroundColor: "#1e293b", color: "white" }} required
            />
            <button type="submit" style={{ padding: "12px", backgroundColor: isRegistering ? "#0284c7" : "#16a34a", color: "white", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold", marginTop: "10px" }}>
              {isRegistering ? "CREATE ACCOUNT" : "INITIALIZE CONNECTION"}
            </button>
            <p onClick={() => { setIsRegistering(!isRegistering); setError(''); }} style={{ textAlign: "center", color: "#38bdf8", cursor: "pointer", fontSize: "14px", marginTop: "10px", textDecoration: "underline" }}>
              {isRegistering ? "Already have an account? Log In" : "Request Access (Sign Up)"}
            </p>
            {error && <p style={{ color: error.includes("✅") ? "#00ff00" : "#ef4444", textAlign: "center", marginTop: "10px", fontWeight: "bold" }}>{error}</p>}
          </form>
        ) : (
          <div style={{ textAlign: 'center', padding: '30px', backgroundColor: '#1e293b', borderRadius: '8px', border: '1px solid #16a34a' }}>
            <div style={{ width: '70px', height: '70px', borderRadius: '50%', backgroundColor: '#16a34a', margin: '0 auto 20px auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '30px' }}>🧑‍💻</div>
            <h2 style={{ margin: '0 0 10px 0' }}>Access Granted</h2>
            <p style={{ color: '#00ff00', margin: '0 0 30px 0', wordWrap: 'break-word' }}>🟢 Sentinel Online:<br />{email}</p>
            <button onClick={handleLogout} style={{ padding: "12px", backgroundColor: "#ef4444", color: "white", border: "none", borderRadius: "5px", cursor: "pointer", width: "100%", fontWeight: "bold" }}>DISCONNECT</button>
          </div>
        )}
      </div>

      {/* 📡 RIGHT SIDE: Live Threat Feed */}
      <div style={{ width: '65%', padding: '40px', display: 'flex', flexDirection: 'column', height: '100vh', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #334155', paddingBottom: '20px', marginBottom: '20px' }}>
          <h2 style={{ margin: 0 }}>Global Threat Feed</h2>
          <span style={{ color: '#00ff00', border: '1px solid #00ff00', padding: '5px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold' }}>● LIVE STREAM</span>
        </div>

        <ul style={{ listStyleType: "none", padding: 0, margin: 0, fontSize: "16px", overflowY: 'auto', flexGrow: 1 }}>
          {logs.length === 0 ? (
            <li style={{ color: "#94a3b8", textAlign: 'center', marginTop: '50px' }}>System Initialized. Monitoring active network traffic...</li>
          ) : (
            logs.map((log, index) => {
              const lowerLog = log.toLowerCase();
              const isLogin = lowerLog.includes("logged in") || lowerLog.includes("online");
              const isLogout = lowerLog.includes("logged out") || lowerLog.includes("offline");
              const isCritical = lowerLog.includes("critical") || lowerLog.includes("brute force");

              const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/gi;
              const foundEmail = log.match(emailRegex);
              const userEmail = foundEmail ? foundEmail[0] : "Sentinel";

              return (
                <li key={index} style={{
                  marginBottom: "12px", padding: "15px", backgroundColor: "#0f172a", borderRadius: "5px",
                  display: "flex", flexDirection: "column", gap: "8px",
                  borderLeft: isCritical ? "5px solid #ef4444" : isLogin ? "5px solid #00ff00" : isLogout ? "5px solid #94a3b8" : "5px solid #38bdf8"
                }}>
                  <span style={{ color: isCritical ? "#ef4444" : "#ffffff", fontWeight: isCritical ? "bold" : "normal" }}>
                    {log}
                  </span>

                  {isLogin && (
                    <span style={{ color: "#00ff00", fontSize: "12px", fontWeight: "bold", borderTop: "1px solid #334155", paddingTop: "5px" }}>
                      ✅ {userEmail} is ONLINE
                    </span>
                  )}

                  {isLogout && (
                    <span style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "bold", borderTop: "1px solid #334155", paddingTop: "5px" }}>
                      🛑 {userEmail} is OFFLINE
                    </span>
                  )}
                </li>
              );
            })
          )}
        </ul>
      </div>
    </div>
  )
}

export default App