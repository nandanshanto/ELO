import React, { useState, useEffect, useRef } from 'react';

function CircularGauge({ percent, label }) {
      const safePercent = Math.min(100, Math.max(0, Number(percent) || 0));
      const radius = 28;
      const circumference = 2 * Math.PI * radius;
      const arcLength = circumference * 0.75;
      const strokeDashoffset = arcLength - (safePercent / 100) * arcLength;

      return (
        <div className="gauge-item">
          <div className="gauge-svg-wrap">
            <svg width="72" height="72" viewBox="0 0 72 72" style={{ transform: "rotate(135deg)" }}>
              <defs>
                <linearGradient id={`grad-${label}`} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#f0abfc" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <circle
                cx="36"
                cy="36"
                r={radius}
                fill="transparent"
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="6"
                strokeDasharray={`${arcLength} ${circumference}`}
                strokeLinecap="round"
              />
              <circle
                cx="36"
                cy="36"
                r={radius}
                fill="transparent"
                stroke={`url(#grad-${label})`}
                strokeWidth="6"
                strokeDasharray={`${arcLength} ${circumference}`}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{
                  transition: "stroke-dashoffset 0.5s ease",
                  filter: "drop-shadow(0 0 6px rgba(192,132,252,0.75))"
                }}
              />
            </svg>
            <span className="gauge-value">{safePercent}%</span>
          </div>
          <span className="gauge-label">{label}</span>
        </div>
      );
    }

    function App() {
      const [topInput, setTopInput] = useState("");
      const [bottomInput, setBottomInput] = useState("");
      const [messages, setMessages] = useState([]);
      const [busy, setBusy] = useState(false);

      const [tasksOpen, setTasksOpen] = useState(false);
      const [recentChats, setRecentChats] = useState([
        "Hi there, Sir an ...",
        "Recent help yo..."
      ]);

      const [ollamaOnline, setOllamaOnline] = useState(true);
      const [voiceEnabled, setVoiceEnabled] = useState(true);
      const [cpu, setCpu] = useState(28);
      const [ram, setRam] = useState(23);
      const [drives, setDrives] = useState([]);
      const [sentinelRunning, setSentinelRunning] = useState(false);
      const [sentinelFile, setSentinelFile] = useState("document.txt");
      const [sentinelTime, setSentinelTime] = useState("10:33 AM");
      const [sentinelLogs, setSentinelLogs] = useState([]);
      const [memoryData, setMemoryData] = useState({
        user_name: "",
        profile: {},
        preferences: {},
        memories: []
      });

      const [showMemoryModal, setShowMemoryModal] = useState(false);
      const [showSysDetails, setShowSysDetails] = useState(false);
      const [showSentinelDetails, setShowSentinelDetails] = useState(false);
      const [isRecording, setIsRecording] = useState(false);

      // Minimizable State for System Monitor & Sentinel
      const [sysMinimized, setSysMinimized] = useState(false);
      const [sentinelMinimized, setSentinelMinimized] = useState(false);

      // Movable Coordinates (relative to center-stage container)
      const [sysPos, setSysPos] = useState({ x: null, y: 18 });
      const [sentinelPos, setSentinelPos] = useState({ x: null, y: 228 });
      const [draggingWidget, setDraggingWidget] = useState(null);
      const dragOffset = useRef({ x: 0, y: 0 });

      const centerStageRef = useRef(null);
      const chatFeedRef = useRef(null);
      const fileInputRef = useRef(null);

      const fetchSystemState = async () => {
        try {
          const res = await fetch("/api/state");
          if (!res.ok) return;
          const data = await res.json();
          setCpu(data.cpu ?? 28);
          setRam(data.ram ?? 23);
          setDrives(data.drives || []);
          setOllamaOnline(Boolean(data.ollama_online));
          setVoiceEnabled(Boolean(data.voice_enabled));
          setSentinelRunning(Boolean(data.sentinel_running));
          setSentinelFile(data.sentinel_file || "document.txt");
          setSentinelTime(data.sentinel_time || "10:33 AM");
          setSentinelLogs(data.sentinel_logs || []);
          if (data.memory) {
            setMemoryData(data.memory);
          }
          if (Array.isArray(data.recent_chats) && data.recent_chats.length > 0) {
            setRecentChats(data.recent_chats);
          }
        } catch (err) {}
      };

      useEffect(() => {
        fetchSystemState();
        const timer = setInterval(fetchSystemState, 2500);
        return () => clearInterval(timer);
      }, []);

      // Safe internal scrolling ONLY inside .chat-feed (never shifts the page!)
      useEffect(() => {
        if (chatFeedRef.current) {
          chatFeedRef.current.scrollTop = chatFeedRef.current.scrollHeight;
        }
      }, [messages, busy]);

      // Dragging logic bounded cleanly inside centerStageRef
      useEffect(() => {
        const handleMouseMove = (e) => {
          if (!draggingWidget || !centerStageRef.current) return;
          const stageRect = centerStageRef.current.getBoundingClientRect();
          const widgetWidth = 230;
          const maxLeft = Math.max(10, stageRect.width - widgetWidth - 10);
          const maxTop = Math.max(10, stageRect.height - 60);

          const newX = Math.max(10, Math.min(maxLeft, e.clientX - stageRect.left - dragOffset.current.x));
          const newY = Math.max(10, Math.min(maxTop, e.clientY - stageRect.top - dragOffset.current.y));

          if (draggingWidget === "sys") {
            setSysPos({ x: newX, y: newY });
          } else if (draggingWidget === "sentinel") {
            setSentinelPos({ x: newX, y: newY });
          }
        };

        const handleMouseUp = () => {
          if (draggingWidget) {
            setDraggingWidget(null);
          }
        };

        window.addEventListener("mousemove", handleMouseMove);
        window.addEventListener("mouseup", handleMouseUp);
        return () => {
          window.removeEventListener("mousemove", handleMouseMove);
          window.removeEventListener("mouseup", handleMouseUp);
        };
      }, [draggingWidget]);

      const startDrag = (widgetKey, e) => {
        if (e.target.closest("button")) return;
        const widgetEl = e.currentTarget.parentElement;
        const rect = widgetEl.getBoundingClientRect();
        dragOffset.current = {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        };
        setDraggingWidget(widgetKey);
      };

      const resetWidgetPositions = () => {
        setSysPos({ x: null, y: 18 });
        setSentinelPos({ x: null, y: 228 });
      };

      const sendCommand = async (rawText, source = "custom") => {
        const text = rawText.trim();
        if (!text || busy) return;

        if (source === "top") setTopInput("");
        if (source === "bottom") setBottomInput("");

        const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setMessages((prev) => [...prev, { role: "user", content: text, time: nowStr }]);
        setBusy(true);

        try {
          const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
          });
          const data = await res.json();
          const replyTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.reply || "No response received.", time: replyTime }
          ]);
          fetchSystemState();
        } catch (err) {
          const replyTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "Could not reach ELO local backend. Make sure `python gui.py` is running.",
              time: replyTime
            }
          ]);
        } finally {
          setBusy(false);
        }
      };

      const toggleSentinel = async (action) => {
        try {
          const res = await fetch(`/api/sentinel/${action}`, { method: "POST" });
          const data = await res.json();
          if (data.message) {
            const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            setMessages((prev) => [...prev, { role: "assistant", content: data.message, time: nowStr }]);
          }
          fetchSystemState();
        } catch (e) {}
      };

      const handleToggleVoice = async () => {
        try {
          const res = await fetch("/api/voice/toggle", { method: "POST" });
          const data = await res.json();
          setVoiceEnabled(Boolean(data.voice_enabled));
        } catch (e) {}
      };

      const handleSpeakText = async (text) => {
        try {
          await fetch("/api/voice/speak", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
          });
        } catch (e) {}
      };

      const handleMicInput = (targetBox) => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          handleSpeakText("Hello! I am ELO. My voice system is online.");
          return;
        }
        if (isRecording) {
          setIsRecording(false);
          return;
        }
        const recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.interimResults = false;
        setIsRecording(true);
        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          if (targetBox === "top") setTopInput(transcript);
          else setBottomInput(transcript);
          setIsRecording(false);
        };
        recognition.onerror = () => setIsRecording(false);
        recognition.onend = () => setIsRecording(false);
        recognition.start();
      };

      const handleFileUpload = (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
          const snippet = String(reader.result || "").slice(0, 1500);
          const promptText = `Analyze this file (${file.name}):\n${snippet}`;
          setTopInput(promptText);
        };
        reader.readAsText(file);
        e.target.value = "";
      };

      const handleClearChat = async () => {
        if (busy) return;
        setMessages([]);
        try {
          await fetch("/api/history/clear", { method: "POST" });
          fetchSystemState();
        } catch (e) {}
      };

      const handleExportChat = () => {
        if (messages.length === 0) return;
        const content = messages
          .map((m) => `${m.role === "user" ? "YOU" : "ELO"} (${m.time}):\n${m.content}`)
          .join("\n\n");
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `ELO_chat_${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "_")}.txt`;
        a.click();
        URL.revokeObjectURL(url);
      };

      const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen?.();
        } else {
          document.exitFullscreen?.();
        }
      };

      return (
        <div className="elo-window">
          <div className="wave-bg"></div>
          <div className="wave-ribbon-1"></div>
          <div className="wave-ribbon-2"></div>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileUpload}
          />

          {/* ================= TOP TITLE BAR ================= */}
          <header className="titlebar">
            <div className="titlebar-left">
              <div className="orb-icon"></div>
              <span className="brand-title">ELO</span>
              <div className="titlebar-divider"></div>
              <button
                className={`titlebar-nav-btn ${messages.length === 0 ? "active" : ""}`}
                onClick={() => setMessages([])}
                title="Return to Home Screen"
              >
                Home
              </button>

              <div className="status-pill" title="Ollama Local AI Connection Status">
                <span
                  className={`status-dot ${
                    busy ? "busy" : ollamaOnline ? "online" : "offline"
                  }`}
                ></span>
                <span>
                  {busy
                    ? "PROCESSING..."
                    : ollamaOnline
                    ? "LOCAL AI ONLINE"
                    : "LOCAL AI OFFLINE"}
                </span>
              </div>

              <button
                className="titlebar-nav-btn"
                onClick={handleToggleVoice}
                title="Toggle ELO Voice Speaker Output"
                style={{ fontSize: "12px", color: voiceEnabled ? "#a78bfa" : "#64748b" }}
              >
                {voiceEnabled ? "🔊 Voice On" : "🔇 Voice Muted"}
              </button>
            </div>

            <div className="window-controls">
              <button
                className="win-btn"
                title="Minimize / Restore Right Widgets"
                onClick={() => {
                  const nextState = !(sysMinimized && sentinelMinimized);
                  setSysMinimized(nextState);
                  setSentinelMinimized(nextState);
                }}
              >
                —
              </button>
              <button className="win-btn" title="Toggle Fullscreen" onClick={toggleFullscreen}>
                ▢
              </button>
              <button
                className="win-btn close"
                title="Close Window"
                onClick={() => window.close()}
              >
                ✕
              </button>
            </div>
          </header>

          {/* ================= MAIN WORKSPACE ================= */}
          <div className="workspace">
            {/* LEFT SIDEBAR */}
            <aside className="sidebar">
              <div className="sidebar-top">
                <div className="sidebar-brand" onClick={() => setMessages([])}>
                  <div className="orb-icon large"></div>
                  <span>ELO</span>
                </div>

                <div
                  className="nav-dropdown"
                  onClick={() => setTasksOpen(!tasksOpen)}
                  title="Click to toggle Quick Desktop Tasks & Actions"
                >
                  <div className="nav-dropdown-left">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <span>Chats & Tasks</span>
                  </div>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    style={{
                      transform: tasksOpen ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.2s"
                    }}
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>

                {tasksOpen && (
                  <div className="tasks-menu">
                    <button className="task-btn" onClick={() => sendCommand("open notepad")}>
                      📝 Open Notepad
                    </button>
                    <button className="task-btn" onClick={() => sendCommand("open calculator")}>
                      🧮 Calculator
                    </button>
                    <button className="task-btn" onClick={() => sendCommand("open file explorer")}>
                      📁 File Explorer
                    </button>
                    <button className="task-btn" onClick={() => sendCommand("open browser")}>
                      🌐 Open Browser
                    </button>
                    <button className="task-btn" onClick={() => sendCommand("system info")}>
                      💻 System Info
                    </button>
                    <button className="task-btn" onClick={() => sendCommand("show memory")}>
                      🧠 Show Memory
                    </button>
                    <button
                      className="task-btn"
                      onClick={() => handleSpeakText("Hello! I am ELO. My voice system is online.")}
                    >
                      🔊 Test Voice
                    </button>
                    <button className="task-btn" onClick={handleExportChat}>
                      💾 Export Chat
                    </button>
                    <button className="task-btn" onClick={handleClearChat}>
                      🗑️ Clear Chat
                    </button>
                    <button className="task-btn" onClick={resetWidgetPositions}>
                      📌 Reset Widgets
                    </button>
                  </div>
                )}

                <div className="recent-section">
                  <div className="recent-header-row">
                    <span className="recent-label">Recent chat</span>
                    {messages.length > 0 && (
                      <button className="mini-action-btn" onClick={handleClearChat} title="Clear Chat">
                        Clear
                      </button>
                    )}
                  </div>

                  {recentChats.map((item, idx) => (
                    <div
                      key={idx}
                      className="recent-item"
                      onClick={() => sendCommand(item.replace(/\.\.\.$/, ""))}
                      title={item}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}>
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                      </svg>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="sidebar-footer">
                <div
                  className="avatar-trigger"
                  onClick={() => setShowMemoryModal(true)}
                  title="Open ELO Memory Core & User Profile"
                >
                  <div className="user-avatar">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="#1e293b">
                      <circle cx="12" cy="8" r="4" />
                      <path d="M4 20c0-4 4-6 8-6s8 2 8 6" />
                    </svg>
                  </div>
                  <div className="user-meta">
                    <span className="user-meta-name">
                      {memoryData.user_name || "Sir"}
                    </span>
                    <span className="user-meta-sub">Memory Core</span>
                  </div>
                </div>
              </div>
            </aside>

            {/* ================= CENTER STAGE ================= */}
            <main
              ref={centerStageRef}
              className={`center-stage ${messages.length > 0 ? "chat-active" : ""}`}
            >
              <div className="hero-container">
                <h1 className="hero-greeting">Hi there, Sir</h1>

                <div className="center-prompt-card">
                  <input
                    type="text"
                    className="center-prompt-input"
                    placeholder="How can I help you today?"
                    value={topInput}
                    disabled={busy}
                    onChange={(e) => setTopInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendCommand(topInput, "top")}
                  />
                  <div className="prompt-actions-row">
                    <button
                      className="icon-btn"
                      title="Attach text/code file"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      +
                    </button>
                    <div className="right-action-group">
                      <button
                        className={`icon-btn ${isRecording ? "recording" : ""}`}
                        onClick={() => handleMicInput("top")}
                        title="Voice Input / Test Voice"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                          <line x1="12" y1="19" x2="12" y2="23"></line>
                          <line x1="8" y1="23" x2="16" y2="23"></line>
                        </svg>
                      </button>
                      <button
                        className="send-btn"
                        disabled={busy}
                        onClick={() => sendCommand(topInput, "top")}
                        title="Send Message"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                          <line x1="22" y1="2" x2="11" y2="13"></line>
                          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Scrollable Chat Feed directly inside Center Stage */}
              {messages.length > 0 && (
                <div className="chat-feed" ref={chatFeedRef}>
                  {messages.map((m, idx) => (
                    <div key={idx} className={`msg-row ${m.role}`}>
                      <div className="msg-meta">
                        <span>{m.role === "user" ? "YOU" : "ELO"} • {m.time}</span>
                        {m.role === "assistant" && (
                          <button
                            className="speak-mini-btn"
                            onClick={() => handleSpeakText(m.content)}
                            title="Speak this response aloud"
                          >
                            🔊
                          </button>
                        )}
                      </div>
                      <div className="msg-bubble">{m.content}</div>
                    </div>
                  ))}
                  {busy && (
                    <div className="msg-row assistant">
                      <div className="msg-meta">ELO • thinking...</div>
                      <div className="msg-bubble" style={{ opacity: 0.75 }}>
                        Processing your request...
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ================= BOTTOM INPUT DOCK ================= */}
              <div className="bottom-dock">
                <button
                  className="icon-btn"
                  title="Attach file"
                  onClick={() => fileInputRef.current?.click()}
                >
                  +
                </button>
                <input
                  type="text"
                  className="bottom-dock-input"
                  placeholder="Ask ELO anything or run a command (e.g., 'show memory', 'system info')..."
                  value={bottomInput}
                  disabled={busy}
                  onChange={(e) => setBottomInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendCommand(bottomInput, "bottom")}
                />
                <div className="right-action-group">
                  <button
                    className={`icon-btn ${isRecording ? "recording" : ""}`}
                    onClick={() => handleMicInput("bottom")}
                    title="Voice Input"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                      <line x1="12" y1="19" x2="12" y2="23"></line>
                      <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                  </button>
                  <button
                    className="send-btn"
                    disabled={busy}
                    onClick={() => sendCommand(bottomInput, "bottom")}
                    title="Send"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <line x1="22" y1="2" x2="11" y2="13"></line>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                  </button>
                </div>
              </div>

              {/* ================= MOVABLE & MINIMIZABLE WIDGET 1: SYSTEM MONITOR ================= */}
              <div
                className={`floating-widget ${sysMinimized ? "minimized" : ""} ${
                  draggingWidget === "sys" ? "dragging" : ""
                }`}
                style={{
                  top: `${sysPos.y}px`,
                  ...(sysPos.x !== null
                    ? { left: `${sysPos.x}px` }
                    : { right: "20px" })
                }}
              >
                <div
                  className="widget-header"
                  onMouseDown={(e) => startDrag("sys", e)}
                  title="Drag to move System Monitor anywhere"
                >
                  <div className="widget-title-wrap">
                    <span className="widget-title">System Monitor</span>
                    {sysMinimized && (
                      <span className="minimized-summary">
                        {cpu}% | {ram}%
                      </span>
                    )}
                  </div>
                  <div className="widget-controls">
                    <button
                      className="widget-ctrl-btn"
                      onClick={() => setSysMinimized(!sysMinimized)}
                      title={sysMinimized ? "Expand System Monitor" : "Minimize System Monitor"}
                    >
                      {sysMinimized ? "+" : "—"}
                    </button>
                    <button
                      className="widget-ctrl-btn"
                      onClick={() => {
                        if (sysMinimized) setSysMinimized(false);
                        setShowSysDetails(!showSysDetails);
                      }}
                      title="Toggle Disk Drive Info"
                    >
                      •••
                    </button>
                  </div>
                </div>

                {!sysMinimized && (
                  <>
                    <div className="widget-divider"></div>
                    <div className="status-pill-bar"></div>
                    <div className="gauges-row">
                      <CircularGauge percent={cpu} label="CPU" />
                      <CircularGauge percent={ram} label="RAM" />
                    </div>
                    {showSysDetails && drives.length > 0 && (
                      <div className="drive-stats-box">
                        {drives.map((d, i) => (
                          <div key={i}>{d}</div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* ================= MOVABLE & MINIMIZABLE WIDGET 2: SENTINEL ================= */}
              <div
                className={`floating-widget ${sentinelMinimized ? "minimized" : ""} ${
                  draggingWidget === "sentinel" ? "dragging" : ""
                }`}
                style={{
                  top: `${sentinelPos.y}px`,
                  ...(sentinelPos.x !== null
                    ? { left: `${sentinelPos.x}px` }
                    : { right: "20px" })
                }}
              >
                <div
                  className="widget-header"
                  onMouseDown={(e) => startDrag("sentinel", e)}
                  title="Drag to move Sentinel widget anywhere"
                >
                  <div className="widget-title-wrap">
                    <span className="widget-title">Sentinel</span>
                    {sentinelMinimized && (
                      <span className="minimized-summary">{sentinelFile}</span>
                    )}
                  </div>
                  <div className="widget-controls">
                    <button
                      className="widget-ctrl-btn"
                      onClick={() => setSentinelMinimized(!sentinelMinimized)}
                      title={sentinelMinimized ? "Expand Sentinel" : "Minimize Sentinel"}
                    >
                      {sentinelMinimized ? "+" : "—"}
                    </button>
                    <button
                      className="widget-ctrl-btn"
                      onClick={() => {
                        if (sentinelMinimized) setSentinelMinimized(false);
                        setShowSentinelDetails(!showSentinelDetails);
                      }}
                      title="Toggle Sentinel Controls & Event Feed"
                    >
                      •••
                    </button>
                  </div>
                </div>

                {!sentinelMinimized && (
                  <>
                    <div className="widget-divider"></div>
                    <div className="sentinel-filename">{sentinelFile}</div>
                    <div className="sentinel-time">last edited - {sentinelTime}</div>

                    {showSentinelDetails && (
                      <div className="sentinel-expanded">
                        <div style={{ fontSize: "11px", color: sentinelRunning ? "#4ade80" : "#facc15" }}>
                          STATUS: {sentinelRunning ? "RUNNING" : "STOPPED"}
                        </div>
                        <div className="sentinel-btn-row">
                          <button
                            className={`sentinel-action-btn ${sentinelRunning ? "active" : ""}`}
                            onClick={() => toggleSentinel("start")}
                          >
                            START
                          </button>
                          <button
                            className={`sentinel-action-btn ${!sentinelRunning ? "active" : ""}`}
                            onClick={() => toggleSentinel("stop")}
                          >
                            STOP
                          </button>
                        </div>
                        <div className="sentinel-log-box">
                          {sentinelLogs.length > 0
                            ? sentinelLogs.join("\n\n")
                            : "No file events recorded yet."}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </main>
          </div>

          {/* ================= MEMORY CORE MODAL ================= */}
          {showMemoryModal && (
            <div className="modal-backdrop" onClick={() => setShowMemoryModal(false)}>
              <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <span style={{ fontWeight: 600, fontSize: "15px" }}>
                    ELO Memory Core & Profile
                  </span>
                  <button
                    className="win-btn"
                    onClick={() => setShowMemoryModal(false)}
                  >
                    ✕
                  </button>
                </div>
                <div className="modal-body">
                  <div className="mem-stat-grid">
                    <div className="mem-stat-box">
                      <div className="mem-stat-label">USER NAME</div>
                      <div className="mem-stat-val">
                        {memoryData.user_name || "Not set"}
                      </div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-label">SAVED MEMORIES</div>
                      <div className="mem-stat-val">
                        {(memoryData.memories || []).length}
                      </div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-label">PROFILE FIELDS</div>
                      <div className="mem-stat-val">
                        {Object.keys(memoryData.profile || {}).length}
                      </div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-label">PREFERENCES</div>
                      <div className="mem-stat-val">
                        {Object.keys(memoryData.preferences || {}).length}
                      </div>
                    </div>
                  </div>

                  <div className="mem-list">
                    <strong style={{ color: "#e9d5ff" }}>Saved Memories:</strong>
                    <br />
                    {(memoryData.memories || []).length > 0
                      ? memoryData.memories.map((m, i) => <div key={i}>• {m}</div>)
                      : "No saved memories yet. Try saying 'remember I love coding'."}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

export default App;
