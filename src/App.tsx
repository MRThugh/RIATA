import React, { useState, useRef, useEffect } from "react";
import {
  Terminal,
  FolderOpen,
  Music,
  Send,
  ShieldCheck,
  Cpu,
  Trash2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Play,
  RotateCcw,
  Layers,
  FileCode,
  Github,
  Monitor,
  Check,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  intentName?: string;
  confidence?: number;
  entities?: Record<string, any>;
  direction: "rtl" | "ltr";
  timestamp: string;
  status?: string;
  executed?: boolean;
  isError?: boolean;
  isDangerous?: boolean;
}

export function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "سلام! به R.I.A.T.A خوش آمدید.\nمن دستیار هوشمند، محلی و بدون هوش‌مصنوعی ابری اوبونتو هستم.\n\nمی‌توانید به فارسی یا انگلیسی فرمان دهید:\n• «فایرفاکس رو باز کن» یا \"Open Firefox\"\n• «پوشه Downloads رو باز کن»\n• «آهنگ Another Love رو پخش کن»\n• «مشخصات سیستم» یا \"System info\"\n\nچه کاری برات انجام بدم؟",
      intentName: "ONLINE",
      confidence: 1.0,
      direction: "rtl",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const [input, setInput] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "inspector" | "tests" | "docs">("chat");
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastIntent, setLastIntent] = useState<any>(null);
  const [testOutput, setTestOutput] = useState<string>("");
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [systemLogs, setSystemLogs] = useState<string[]>([]);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (commandText?: string) => {
    const textToSend = (commandText || input).trim();
    if (!textToSend || isProcessing) return;

    setInput("");
    const isPersian = /[\u0600-\u06FF]/.test(textToSend);
    const userDir: "rtl" | "ltr" = isPersian ? "rtl" : "ltr";

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      sender: "user",
      text: textToSend,
      direction: userDir,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    try {
      const res = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: textToSend, dry_run: dryRun }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setLastIntent(data.intent);
      if (data.logs) {
        setSystemLogs(data.logs);
      }

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: data.response,
        intentName: data.intent?.name || "UNKNOWN",
        confidence: data.intent?.confidence || 0,
        entities: data.intent?.entities,
        direction: data.direction || "ltr",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        status: data.status || (data.success ? "SUCCESS" : "FAILED"),
        executed: data.executed || false,
        isError: !data.success,
        isDangerous: data.intent?.is_dangerous,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      // Truthful error reporting when backend is offline - NEVER fake success!
      const assistantMsg: Message = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text: isPersian
          ? "⚠ خطا: هسته R.I.A.T.A در دسترس نیست. فرمان اجرا نگردید."
          : `⚠ Error: R.I.A.T.A backend is unavailable. Command was NOT executed. (${err.message || "Network Error"})`,
        intentName: "BACKEND_UNAVAILABLE",
        status: "BACKEND_UNAVAILABLE",
        direction: isPersian ? "rtl" : "ltr",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isError: true,
        executed: false,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const runPytest = async () => {
    setIsRunningTests(true);
    setTestOutput("Running 'pytest -v' against full test suite...\n");
    try {
      const res = await fetch("/api/run-tests");
      const data = await res.json();
      setTestOutput(data.output || "Test completed.");
    } catch (err: any) {
      setTestOutput(`Error running tests: ${err.message}`);
    } finally {
      setIsRunningTests(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "welcome-reset",
        sender: "assistant",
        text: "سلام! گفت‌وگو بازنشانی شد. چه کاری برات انجام بدم؟",
        intentName: "ONLINE",
        direction: "rtl",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  const examplePrompts = [
    { label: "فایرفاکس رو باز کن", dir: "rtl" },
    { label: "Open Firefox", dir: "ltr" },
    { label: "Downloads رو باز کن", dir: "rtl" },
    { label: "آهنگ Another Love رو پخش کن", dir: "rtl" },
    { label: "مشخصات سیستم", dir: "rtl" },
    { label: "sudo rm -rf /", dir: "ltr", badge: "🛡️ Safe Block" },
  ];

  return (
    <div className="flex h-screen w-screen bg-[#0b0f19] text-slate-100 font-sans overflow-hidden">
      {/* Main Container */}
      <div className="flex flex-col flex-1 h-full min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-[#111827] border-b border-slate-800 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400">
              <Monitor className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sky-400 text-lg tracking-wider">R.I.A.T.A</span>
                <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-700">v0.1.1</span>
                <span className="text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  ONLINE
                </span>
                {dryRun && (
                  <span className="text-xs bg-amber-950/80 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-semibold">
                    DRY RUN
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Responsive Intent Automation & Task Assistant • Created by <span className="text-slate-200 font-medium">Ali Kamrani (MRThugh)</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Navigation Tabs */}
            <div className="flex bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                onClick={() => setActiveTab("chat")}
                className={`px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === "chat" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Chat UI
              </button>
              <button
                onClick={() => setActiveTab("inspector")}
                className={`px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === "inspector" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Engine Inspector
              </button>
              <button
                onClick={() => setActiveTab("tests")}
                className={`px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === "tests" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Unit Tests
              </button>
              <button
                onClick={() => setActiveTab("docs")}
                className={`px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === "docs" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Docs
              </button>
            </div>

            {/* Dry Run Toggle */}
            <button
              onClick={() => setDryRun(!dryRun)}
              title="Toggle Dry-Run Simulation"
              className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition ${
                dryRun
                  ? "bg-amber-900/40 border-amber-700/60 text-amber-300"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
              }`}
            >
              Dry Run: {dryRun ? "ON" : "OFF"}
            </button>

            {/* Clear Button */}
            <button
              onClick={clearChat}
              title="Clear chat timeline"
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Tab Content */}
        {activeTab === "chat" && (
          <div className="flex flex-col flex-1 h-[calc(100vh-4rem)] overflow-hidden">
            {/* Quick Action Chips */}
            <div className="bg-[#0e1422] border-b border-slate-800/80 px-6 py-2.5 flex items-center gap-2 overflow-x-auto text-xs shrink-0">
              <span className="text-slate-400 font-medium whitespace-nowrap flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" /> تست سریع / Examples:
              </span>
              {examplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(p.label)}
                  className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700/80 px-2.5 py-1 rounded-full whitespace-nowrap transition flex items-center gap-1.5"
                  dir={p.dir}
                >
                  <span>{p.label}</span>
                  {p.badge && (
                    <span className="text-[10px] bg-red-950/80 text-red-300 border border-red-800 px-1 rounded">
                      {p.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Chat Timeline */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.sender === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] sm:max-w-xl rounded-2xl p-4 shadow-lg transition ${
                      msg.sender === "user"
                        ? "bg-blue-700 text-white rounded-br-sm border border-blue-600"
                        : msg.isDangerous
                        ? "bg-red-950/80 text-red-100 rounded-bl-sm border border-red-800"
                        : "bg-[#161e2e] text-slate-100 rounded-bl-sm border border-slate-800"
                    }`}
                  >
                    {/* Assistant Header */}
                    {msg.sender === "assistant" && (
                      <div className="flex items-center justify-between gap-3 mb-2 pb-2 border-b border-slate-700/40 text-xs">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-sky-400 tracking-wider">R.I.A.T.A</span>
                          {msg.intentName && (
                            <span className="bg-slate-900 border border-slate-700 text-sky-300 px-2 py-0.5 rounded font-mono text-[11px]">
                              {msg.intentName}
                            </span>
                          )}
                          {msg.status === "BACKEND_UNAVAILABLE" && (
                            <span className="bg-red-950 border border-red-800 text-red-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              ⚠ BACKEND UNAVAILABLE
                            </span>
                          )}
                          {(msg.status === "PERMISSION_DENIED" || msg.isDangerous) && (
                            <span className="bg-red-950 border border-red-800 text-red-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              🛡️ BLOCKED
                            </span>
                          )}
                          {msg.status === "PATH_NOT_ALLOWED" && (
                            <span className="bg-amber-950 border border-amber-800 text-amber-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              🚫 PATH NOT ALLOWED
                            </span>
                          )}
                          {msg.status === "APP_NOT_FOUND" && (
                            <span className="bg-amber-950 border border-amber-800 text-amber-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              NOT FOUND
                            </span>
                          )}
                          {msg.executed && (
                            <span className="bg-emerald-950 border border-emerald-800 text-emerald-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              ⚡ EXECUTED
                            </span>
                          )}
                          {msg.confidence !== undefined && msg.confidence > 0 && (
                            <span className="text-slate-400 text-[10px]">
                              {(msg.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                        <span className="text-slate-400 text-[10px]">{msg.timestamp}</span>
                      </div>
                    )}

                    {/* Message Body */}
                    <div
                      className="text-sm whitespace-pre-wrap leading-relaxed"
                      dir={msg.direction}
                    >
                      {msg.text}
                    </div>

                    {/* User Timestamp */}
                    {msg.sender === "user" && (
                      <div className="text-[10px] text-blue-200/80 text-right mt-1.5">
                        {msg.timestamp}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatBottomRef} />
            </div>

            {/* Input Bar */}
            <div className="bg-[#111827] border-t border-slate-800 p-4 shrink-0">
              <div className="max-w-4xl mx-auto flex items-end gap-3">
                <div className="flex-1 relative bg-[#1e293b] rounded-xl border border-slate-700 focus-within:border-sky-500 transition">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="پیام خود را بنویسید... (Enter برای ارسال) / Type command (e.g. Open Firefox)..."
                    rows={1}
                    className="w-full bg-transparent text-slate-100 placeholder-slate-400 text-sm p-3.5 resize-none focus:outline-none min-h-[46px] max-h-32"
                  />
                </div>
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isProcessing}
                  className="h-[46px] px-5 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium rounded-xl flex items-center justify-center gap-2 transition shadow-lg shrink-0"
                >
                  <Send className="w-4 h-4" />
                  <span className="hidden sm:inline">ارسال / Send</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Engine Inspector Tab */}
        {activeTab === "inspector" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-6">
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-bold text-sky-400 flex items-center gap-2 mb-2">
                <Layers className="w-5 h-5" /> Last Parsed Intent
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                Demonstrates the separation of language understanding and entity extraction from execution.
              </p>

              {lastIntent ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                      <div className="text-xs text-slate-400">Intent Name</div>
                      <div className="text-base font-bold text-sky-300 font-mono mt-1">
                        {lastIntent.name}
                      </div>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                      <div className="text-xs text-slate-400">Confidence</div>
                      <div className="text-base font-bold text-emerald-400 font-mono mt-1">
                        {lastIntent.confidence}
                      </div>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                      <div className="text-xs text-slate-400">Language</div>
                      <div className="text-base font-bold text-amber-300 font-mono mt-1 uppercase">
                        {lastIntent.language}
                      </div>
                    </div>
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                      <div className="text-xs text-slate-400">Is Dangerous?</div>
                      <div className={`text-base font-bold font-mono mt-1 ${lastIntent.is_dangerous ? "text-red-400" : "text-emerald-400"}`}>
                        {lastIntent.is_dangerous ? "YES (BLOCKED)" : "NO (SAFE)"}
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-900/90 p-4 rounded-lg border border-slate-800 font-mono text-xs overflow-x-auto text-slate-300">
                    <div className="text-slate-400 mb-1">// Full Intent Object:</div>
                    <pre>{JSON.stringify(lastIntent, null, 2)}</pre>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-400 p-6 text-center border border-dashed border-slate-800 rounded-lg">
                  Send a command in the Chat UI to inspect real-time Intent Engine breakdown.
                </div>
              )}
            </div>

            {/* Live System Logs */}
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-bold text-sky-400 flex items-center gap-2 mb-2">
                <FileCode className="w-5 h-5" /> Recent Engine Logs
              </h2>
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs text-emerald-400 h-48 overflow-y-auto space-y-1">
                {systemLogs.length > 0 ? (
                  systemLogs.map((log, i) => <div key={i}>{log}</div>)
                ) : (
                  <div className="text-slate-500">// Waiting for commands to generate logs...</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Unit Tests Tab */}
        {activeTab === "tests" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-sky-400">Automated pytest Test Suite</h2>
                <p className="text-xs text-slate-400">
                  Tests Persian normalization, English matching, entity extraction, folder security, and dry-run execution.
                </p>
              </div>
              <button
                onClick={runPytest}
                disabled={isRunningTests}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition"
              >
                <Play className="w-4 h-4" />
                {isRunningTests ? "Running Tests..." : "Run All Tests (pytest -v)"}
              </button>
            </div>

            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 font-mono text-xs text-slate-200 h-[calc(100vh-14rem)] overflow-y-auto whitespace-pre">
              {testOutput || 'Click "Run All Tests" above to execute pytest live against the 67 automated tests.'}
            </div>
          </div>
        )}

        {/* Documentation Tab */}
        {activeTab === "docs" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6 text-sm text-slate-300">
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-6 space-y-4">
              <h2 className="text-xl font-bold text-sky-400">About R.I.A.T.A v0.1.1</h2>
              <p>
                <strong>R.I.A.T.A</strong> (Responsive Intent Automation & Task Assistant) is an open-source Ubuntu Linux desktop assistant built by <strong>Ali Kamrani (MRThugh)</strong>.
              </p>
              <p>
                Version <strong>0.1.1</strong> introduces an extensible Language Pack Registry (completely removing language-specific branching from core logic), an Interaction System with short-lived context disambiguation, a risk-aware Policy Engine (ALLOW, CONFIRM, DENY), and a modular Desktop Capability foundation.
              </p>

              <h3 className="text-base font-semibold text-sky-300 pt-2">How to Run on Ubuntu Desktop:</h3>
              <div className="bg-slate-950 p-3 rounded-lg font-mono text-xs text-slate-200 border border-slate-800">
                python3 -m venv .venv<br />
                source .venv/bin/activate<br />
                pip install -r requirements.txt<br />
                python main.py
              </div>

              <h3 className="text-base font-semibold text-sky-300 pt-2">Developer Modes:</h3>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li><code className="text-sky-300">python main.py --dry-run</code> : Simulate intents without launching Linux processes</li>
                <li><code className="text-sky-300">python main.py --debug</code> : Verbose structured log output</li>
                <li><code className="text-sky-300">python main.py --cli</code> : Run interactive terminal console</li>
                <li><code className="text-sky-300">pytest -v</code> : Execute test suite</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
