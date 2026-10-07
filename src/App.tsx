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
  Monitor,
  Check,
  ChevronRight,
  Sparkles,
  ListTree,
  FileText,
  XCircle,
  ExternalLink,
  BookOpen,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";

interface StepInfo {
  step_id: number;
  raw_text: string;
  intent_name?: string;
  status: "PENDING" | "SUCCESS" | "FAILED" | "BLOCKED" | "SKIPPED" | "CANCELLED";
  dependencies?: number[];
  risk_level?: string;
  action_summary?: string;
  error?: string;
}

interface CommandPlanInfo {
  plan_id: string;
  source_text: string;
  step_count: number;
  status: string;
  steps: StepInfo[];
}

interface SessionContextInfo {
  session_id: string;
  active_app?: string | null;
  active_directory?: string | null;
  active_file?: string | null;
  active_topic?: string | null;
  open_applications?: string[];
  pending_confirmation?: {
    confirmation_id: string;
    action: string;
    action_label?: string;
    status: string;
  } | null;
  history_count?: number;
}

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
  plan?: CommandPlanInfo | null;
  needsConfirmation?: boolean;
  confirmationId?: string;
}

export function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "سلام! به R.I.A.T.A نسخه 0.2.0 خوش آمدید.\nدستیار محلی، تعاملی، مبتنی بر زمینه (Context-Aware) و چندمرحله‌ای برای اوبونتو.\n\nویژگی‌های جدید v0.2.0:\n• درک ارجاعات پیوسته (مثلاً: «کروم رو باز کن» و سپس «ببندش»)\n• برنامه‌ریزی چندمرحله‌ای (مثلاً: «کروم رو باز کن و فایل منیجر رو باز کن»)\n• مدیریت هوشمند رفع ابهام (Clarification)\n• تأیید امنیتی دومرحله‌ای برای دستورات با ریسک بالا (مانند حذف فایل)\n• پاکسازی زمینه («فراموش کن» یا «Reset Context»)\n\nچه کاری برایتان انجام دهم؟",
      intentName: "CONTEXT_ENGINE_ONLINE",
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
  const [lastPlan, setLastPlan] = useState<CommandPlanInfo | null>(null);
  const [sessionContext, setSessionContext] = useState<SessionContextInfo>({
    session_id: "web-companion",
    active_app: null,
    active_directory: null,
    active_file: null,
    open_applications: [],
    pending_confirmation: null,
  });
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
        headers: {
          "Content-Type": "application/json",
          "X-RIATA-Client": "web-v0.2.0",
        },
        body: JSON.stringify({
          text: textToSend,
          dry_run: dryRun,
          session_id: sessionContext.session_id,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setLastIntent(data.intent);
      if (data.plan) {
        setLastPlan(data.plan);
      }
      if (data.context) {
        setSessionContext(data.context);
      }
      if (data.logs) {
        setSystemLogs(data.logs);
      }

      const isNeedsConfirmation = data.status === "NEEDS_CONFIRMATION";
      const confirmationId = data.result?.metadata?.confirmation_id;

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
        isError: !data.success && !isNeedsConfirmation && data.status !== "NEEDS_CLARIFICATION",
        isDangerous: data.intent?.is_dangerous,
        plan: data.plan,
        needsConfirmation: isNeedsConfirmation,
        confirmationId,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const assistantMsg: Message = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text: isPersian
          ? "⚠ خطا: هسته R.I.A.T.A در دسترس نیست یا ارتباط با سرور برقرار نشد."
          : `⚠ Error: R.I.A.T.A backend is unavailable. (${err.message || "Network Error"})`,
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

  const handleResetContext = async () => {
    try {
      await fetch("/api/reset-context", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-RIATA-Client": "web-v0.2.0",
        },
        body: JSON.stringify({ session_id: sessionContext.session_id }),
      });
      setSessionContext({
        session_id: "web-companion",
        active_app: null,
        active_directory: null,
        active_file: null,
        open_applications: [],
        pending_confirmation: null,
      });
      const resetMsg: Message = {
        id: `reset-${Date.now()}`,
        sender: "assistant",
        text: "زمینه گفت‌وگو و حافظه نشست با موفقیت پاکسازی شد. / Context successfully reset.",
        intentName: "RESET_CONTEXT",
        status: "SUCCESS",
        direction: "rtl",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, resetMsg]);
    } catch (err) {
      // Fallback: send text command
      handleSend("فراموش کن");
    }
  };

  const runPytest = async () => {
    setIsRunningTests(true);
    setTestOutput("Running 'pytest -v' against full R.I.A.T.A v0.2.0 test suite (108 unit tests)...\n");
    try {
      const res = await fetch("/api/run-tests", {
        headers: {
          "X-RIATA-Client": "web-v0.2.0",
        },
      });
      const data = await res.json();
      setTestOutput(data.output || "Test execution completed.");
    } catch (err: any) {
      setTestOutput(`Error running pytest: ${err.message}`);
    } finally {
      setIsRunningTests(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "welcome-reset",
        sender: "assistant",
        text: "تاریخچه پیام‌ها پاکسازی شد. چه کاری برایتان انجام دهم؟",
        intentName: "ONLINE",
        direction: "rtl",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  const exampleFlows: Array<{
    category: string;
    items: Array<{
      label: string;
      dir: "rtl" | "ltr";
      badge?: string;
      note?: string;
    }>;
  }> = [
    {
      category: "Multi-Step Planning",
      items: [
        { label: "کروم رو باز کن و فایل منیجر رو باز کن", dir: "rtl" },
        { label: "open Chrome and open Firefox", dir: "ltr" },
        { label: "ترمینال رو باز کن و مشخصات سیستم", dir: "rtl" },
      ],
    },
    {
      category: "Context & Pronouns",
      items: [
        { label: "فایرفاکس رو باز کن", dir: "rtl", note: "مرحله ۱" },
        { label: "ببندش", dir: "rtl", note: "ارجاع به فایرفاکس" },
        { label: "پوشه Downloads رو باز کن", dir: "rtl", note: "زمینه پوشه" },
      ],
    },
    {
      category: "Security Policy & Confirmation",
      items: [
        { label: "فایل report.txt رو حذف کن", dir: "rtl", badge: "نیاز به تأیید" },
        { label: "sudo rm -rf /", dir: "ltr", badge: "🛡️ مسدودسازی مقتدرانه" },
        { label: "فراموش کن", dir: "rtl", badge: "پاکسازی حافظه" },
      ],
    },
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
                <span className="text-xs bg-slate-800 text-slate-200 px-2 py-0.5 rounded font-mono border border-slate-700">
                  v0.2.0
                </span>
                <span className="text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  CONTEXT ENGINE
                </span>
                {dryRun && (
                  <span className="text-xs bg-amber-950/80 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-semibold">
                    DRY RUN
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Context-Aware Interaction Platform • By <span className="text-slate-200 font-medium">Ali Kamrani (MRThugh)</span>
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
                Context Inspector
              </button>
              <button
                onClick={() => setActiveTab("tests")}
                className={`px-3 py-1.5 rounded-md font-medium transition ${
                  activeTab === "tests" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Test Suite (108)
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
              title="Clear message timeline"
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Live Context Bar */}
        <div className="bg-[#0d1322] border-b border-slate-800/80 px-6 py-2 flex items-center justify-between text-xs shrink-0 overflow-x-auto gap-4">
          <div className="flex items-center gap-3 whitespace-nowrap">
            <span className="text-slate-400 font-semibold flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-sky-400" /> وضعیت زمینه نشست:
            </span>
            <div className="flex items-center gap-2">
              <span className="bg-slate-900/90 border border-slate-800 px-2 py-0.5 rounded text-slate-300">
                برنامه فعال:{" "}
                <strong className={sessionContext.active_app ? "text-emerald-400 font-mono" : "text-slate-500"}>
                  {sessionContext.active_app || "هیچ"}
                </strong>
              </span>
              <span className="bg-slate-900/90 border border-slate-800 px-2 py-0.5 rounded text-slate-300">
                پوشه فعال:{" "}
                <strong className={sessionContext.active_directory ? "text-amber-400 font-mono" : "text-slate-500"}>
                  {sessionContext.active_directory || "هیچ"}
                </strong>
              </span>
              <span className="bg-slate-900/90 border border-slate-800 px-2 py-0.5 rounded text-slate-300">
                فایل فعال:{" "}
                <strong className={sessionContext.active_file ? "text-indigo-400 font-mono" : "text-slate-500"}>
                  {sessionContext.active_file || "هیچ"}
                </strong>
              </span>
              {sessionContext.open_applications && sessionContext.open_applications.length > 0 && (
                <span className="bg-slate-900/90 border border-slate-800 px-2 py-0.5 rounded text-sky-300">
                  برنامه‌های باز: <strong>{sessionContext.open_applications.join(", ")}</strong>
                </span>
              )}
              {sessionContext.pending_confirmation && (
                <span className="bg-red-950/80 border border-red-800 px-2 py-0.5 rounded text-red-300 font-medium animate-pulse">
                  ⚠️ منتظر تأیید: {sessionContext.pending_confirmation.action}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={handleResetContext}
            className="text-slate-400 hover:text-amber-300 hover:bg-slate-800 px-2 py-1 rounded transition text-[11px] flex items-center gap-1 border border-transparent hover:border-slate-700 whitespace-nowrap"
          >
            <RotateCcw className="w-3 h-3" />
            پاکسازی زمینه (Reset Context)
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "chat" && (
          <div className="flex flex-col flex-1 h-[calc(100vh-6.5rem)] overflow-hidden">
            {/* Quick Action Chips categorized */}
            <div className="bg-[#0a0e17] border-b border-slate-800/80 px-6 py-2 flex items-center gap-3 overflow-x-auto text-xs shrink-0">
              <span className="text-slate-400 font-medium whitespace-nowrap flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" /> فرمان‌های نمونه:
              </span>
              {exampleFlows.flatMap((c) => c.items).map((p, idx) => (
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
                  {p.note && (
                    <span className="text-[10px] text-slate-400">
                      ({p.note})
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
                    className={`max-w-[85%] sm:max-w-2xl rounded-2xl p-4 shadow-lg transition ${
                      msg.sender === "user"
                        ? "bg-blue-700 text-white rounded-br-sm border border-blue-600"
                        : msg.isDangerous
                        ? "bg-red-950/80 text-red-100 rounded-bl-sm border border-red-800"
                        : msg.needsConfirmation
                        ? "bg-[#1f1917] text-amber-100 rounded-bl-sm border border-amber-800/80"
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
                          {msg.status === "NEEDS_CONFIRMATION" && (
                            <span className="bg-amber-950 border border-amber-700 text-amber-300 px-2 py-0.5 rounded font-semibold text-[10px] flex items-center gap-1">
                              ⚠️ نیاز به تأیید کاربر
                            </span>
                          )}
                          {msg.status === "NEEDS_CLARIFICATION" && (
                            <span className="bg-blue-950 border border-blue-700 text-blue-300 px-2 py-0.5 rounded font-semibold text-[10px]">
                              ❓ ابهام در ارجاع
                            </span>
                          )}
                          {(msg.status === "PERMISSION_DENIED" || msg.isDangerous) && (
                            <span className="bg-red-950 border border-red-800 text-red-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              🛡️ مسدود شد (Policy Denied)
                            </span>
                          )}
                          {msg.status === "PATH_NOT_ALLOWED" && (
                            <span className="bg-amber-950 border border-amber-800 text-amber-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              🚫 خارج از محدوده مجاز
                            </span>
                          )}
                          {msg.status === "APP_NOT_FOUND" && (
                            <span className="bg-amber-950 border border-amber-800 text-amber-300 px-1.5 py-0.5 rounded font-semibold text-[10px]">
                              یافت نشد
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

                    {/* Multi-Step Plan Breakdown */}
                    {msg.plan && msg.plan.steps && msg.plan.steps.length > 1 && (
                      <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2">
                        <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                          <ListTree className="w-3.5 h-3.5 text-sky-400" />
                          برنامه چندمرحله‌ای ({msg.plan.step_count} مرحله):
                        </div>
                        <div className="grid gap-1.5">
                          {msg.plan.steps.map((st) => (
                            <div
                              key={st.step_id}
                              className="bg-slate-900/80 border border-slate-800 rounded p-2 text-xs flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-mono text-[10px]">
                                  {st.step_id}
                                </span>
                                <span className="font-medium text-slate-200">{st.raw_text}</span>
                              </div>
                              <div>
                                {st.status === "SUCCESS" && (
                                  <span className="text-emerald-400 font-semibold text-[11px] flex items-center gap-1">
                                    ✓ موفق
                                  </span>
                                )}
                                {st.status === "FAILED" && (
                                  <span className="text-red-400 font-semibold text-[11px] flex items-center gap-1">
                                    ✕ ناموفق
                                  </span>
                                )}
                                {st.status === "SKIPPED" && (
                                  <span className="text-slate-500 font-semibold text-[11px]">
                                    ⏭ رد شد (عایق خطا)
                                  </span>
                                )}
                                {st.status === "PENDING" && (
                                  <span className="text-amber-400 font-semibold text-[11px]">
                                    ⏳ در انتظار
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Interactive Confirmation Action Bar */}
                    {msg.needsConfirmation && (
                      <div className="mt-3 pt-3 border-t border-amber-800/50 flex items-center gap-2">
                        <button
                          onClick={() => handleSend("بله")}
                          className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow transition"
                        >
                          <Check className="w-3.5 h-3.5" />
                          بله، تأیید و اجرا (Confirm)
                        </button>
                        <button
                          onClick={() => handleSend("خیر")}
                          className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition"
                        >
                          <XCircle className="w-3.5 h-3.5 text-red-400" />
                          خیر، لغو عملیات (Cancel)
                        </button>
                      </div>
                    )}

                    {/* Interactive Disambiguation Quick Choices */}
                    {msg.status === "NEEDS_CLARIFICATION" && sessionContext.open_applications && sessionContext.open_applications.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-1.5">
                        <div className="text-xs text-slate-400">کدام برنامه را مد نظر دارید؟</div>
                        <div className="flex flex-wrap gap-2">
                          {sessionContext.open_applications.map((app, i) => (
                            <button
                              key={i}
                              onClick={() => handleSend(`${app} رو ببند`)}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-sky-600 text-slate-200 hover:text-white rounded text-xs transition border border-slate-700"
                            >
                              بستن {app}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

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
                    placeholder="فرمان خود را بنویسید... مثلاً: «کروم رو باز کن و دانلودها رو باز کن» یا «ببندش» (Enter برای ارسال)..."
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

        {/* Engine & Context Inspector Tab */}
        {activeTab === "inspector" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-6">
            {/* Context Session Inspector */}
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-bold text-sky-400 flex items-center gap-2 mb-2">
                <Layers className="w-5 h-5" /> Session Context State
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                Demonstrates local, isolated multi-turn context tracking (Active entities, Pronoun resolution targets, and Security tokens).
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Active App</div>
                  <div className="text-sm font-bold text-emerald-400 font-mono mt-1">
                    {sessionContext.active_app || "None"}
                  </div>
                </div>
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Active Directory</div>
                  <div className="text-sm font-bold text-amber-400 font-mono mt-1 truncate">
                    {sessionContext.active_directory || "None"}
                  </div>
                </div>
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Active File</div>
                  <div className="text-sm font-bold text-indigo-400 font-mono mt-1 truncate">
                    {sessionContext.active_file || "None"}
                  </div>
                </div>
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs text-slate-400">Open Apps Count</div>
                  <div className="text-sm font-bold text-sky-300 font-mono mt-1">
                    {sessionContext.open_applications?.length || 0}
                  </div>
                </div>
              </div>

              <div className="bg-slate-900/90 p-4 rounded-lg border border-slate-800 font-mono text-xs overflow-x-auto text-slate-300">
                <div className="text-slate-400 mb-1">// Raw Context Snapshot:</div>
                <pre>{JSON.stringify(sessionContext, null, 2)}</pre>
              </div>
            </div>

            {/* Last Multi-Step Plan Inspector */}
            {lastPlan && (
              <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-5">
                <h2 className="text-lg font-bold text-sky-400 flex items-center gap-2 mb-2">
                  <ListTree className="w-5 h-5" /> Command Planner Status
                </h2>
                <div className="bg-slate-900/90 p-4 rounded-lg border border-slate-800 font-mono text-xs overflow-x-auto text-slate-300">
                  <pre>{JSON.stringify(lastPlan, null, 2)}</pre>
                </div>
              </div>
            )}

            {/* Intent Object Inspector */}
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-5">
              <h2 className="text-lg font-bold text-sky-400 flex items-center gap-2 mb-2">
                <Layers className="w-5 h-5" /> Last Parsed Intent
              </h2>
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
                      <div className="text-xs text-slate-400">Dangerous Command?</div>
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
                  ارسال یک فرمان در تب چت برای مشاهده وضعیت Intent Engine.
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
                <h2 className="text-lg font-bold text-sky-400">R.I.A.T.A v0.2.0 Automated Pytest Suite</h2>
                <p className="text-xs text-slate-400">
                  108 automated unit tests covering Context Engine, Entity Resolution, Command Planner, Policy Engine, Capabilities, and Security Regressions.
                </p>
              </div>
              <button
                onClick={runPytest}
                disabled={isRunningTests}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition"
              >
                <Play className="w-4 h-4" />
                {isRunningTests ? "Running Tests..." : "Run All 108 Tests (pytest -v)"}
              </button>
            </div>

            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 font-mono text-xs text-slate-200 h-[calc(100vh-14rem)] overflow-y-auto whitespace-pre">
              {testOutput || 'Click "Run All 108 Tests" above to execute pytest live against the full v0.2.0 test suite.'}
            </div>
          </div>
        )}

        {/* Documentation Tab */}
        {activeTab === "docs" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6 text-sm text-slate-300">
            <div className="bg-[#131b2e] border border-slate-800 rounded-xl p-6 space-y-4">
              <h2 className="text-xl font-bold text-sky-400">R.I.A.T.A v0.2.0 Context-Aware Architecture</h2>
              <p>
                <strong>R.I.A.T.A</strong> (Responsive Intent Automation & Task Assistant) is a local-first, deterministic, rule-based desktop assistant for Ubuntu Linux created by <strong>Ali Kamrani (MRThugh)</strong>.
              </p>
              <p>
                Version <strong>0.2.0</strong> evolves R.I.A.T.A into a full <em>Context-Aware Interaction Platform</em> without compromising deterministic execution, safety boundaries, or local security.
              </p>

              <h3 className="text-base font-semibold text-sky-300 pt-2">v0.2.0 Core Architecture Pipeline:</h3>
              <div className="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-300 border border-slate-800 space-y-1">
                <div>User Input (Persian / English)</div>
                <div className="text-slate-500">  ↓ Normalizer & Language Detection</div>
                <div>Intent Engine (Grammar & Patterns)</div>
                <div className="text-slate-500">  ↓ Context Engine & Entity Resolver</div>
                <div>Command Planner (Multi-step DAG & Dependency Mapping)</div>
                <div className="text-slate-500">  ↓ Policy Engine (ALLOW / CONFIRM / DENY)</div>
                <div>Capability Registry (Applications, Filesystem, Media, Windows...)</div>
                <div className="text-slate-500">  ↓ Executor (Safe subprocess / zero shell=True)</div>
                <div>Operating System (Linux)</div>
              </div>

              <h3 className="text-base font-semibold text-sky-300 pt-2">Security Model Guarantees:</h3>
              <ul className="list-disc pl-5 space-y-1 text-xs">
                <li><strong>Authoritative Policy Engine:</strong> No contextual plan or pronoun resolution may ever bypass security policy.</li>
                <li><strong>Zero shell=True:</strong> Zero arbitrary shell invocations; arguments are strictly tokenized and allowlisted.</li>
                <li><strong>Sandbox Containment:</strong> Filesystem operations are strictly bound to user home (~/) and /tmp, rejecting traversal (`../`) and sensitive dirs (`~/.ssh`, `/etc`).</li>
                <li><strong>Single-Use Confirmation Tokens:</strong> High-risk operations (e.g. DELETE_FILE) require explicit non-replayable confirmation tokens bound to the active session.</li>
              </ul>

              <h3 className="text-base font-semibold text-sky-300 pt-2">How to Run on Ubuntu Desktop:</h3>
              <div className="bg-slate-950 p-3 rounded-lg font-mono text-xs text-slate-200 border border-slate-800">
                python3 -m venv .venv<br />
                source .venv/bin/activate<br />
                pip install -r requirements.txt<br />
                python main.py
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
