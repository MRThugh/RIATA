import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { spawn, ChildProcess } from "child_process";
import http, { IncomingMessage, ServerResponse } from "http";

// Client identifier header used by the companion to route requests.
// NOTE: This header is a client identifier, NOT an authentication mechanism.
const ALLOWED_CLIENT_IDENTIFIERS = new Set(["web-v0.2.0"]);

// Strict loopback hostnames and remote IP addresses (0.0.0.0 and LAN ranges explicitly removed)
const LOOPBACK_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1"]);
const LOOPBACK_IPS = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

// Canonical session ID format validator (1 to 64 alphanumeric characters, underscores, and hyphens)
const SESSION_ID_REGEX = /^[A-Za-z0-9_-]{1,64}$/;

// Persistent Python Backend Configuration
const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = process.env.RIATA_BACKEND_PORT ? parseInt(process.env.RIATA_BACKEND_PORT, 10) : 5005;

let persistentBackendProcess: ChildProcess | null = null;
let isStartingBackend = false;

interface SecurityCheckResult {
  allowed: boolean;
  statusCode: number;
  message: string;
  matchedOrigin?: string;
}

function parseHostname(rawHost: string): string | null {
  if (!rawHost) return null;
  try {
    const parsed = new URL(`http://${rawHost}`);
    let hostname = parsed.hostname.toLowerCase();
    if (hostname.startsWith("[") && hostname.endsWith("]")) {
      hostname = hostname.slice(1, -1);
    }
    return hostname;
  } catch {
    return null;
  }
}

function isAllowedLoopbackHost(hostname: string | null): boolean {
  if (!hostname) return false;
  return LOOPBACK_HOSTNAMES.has(hostname);
}

function validateRequestSecurity(req: IncomingMessage, isOptions: boolean = false): SecurityCheckResult {
  const remoteIp = req.socket?.remoteAddress || "";
  // Strictly permit loopback only. Private LAN addresses (10.x, 172.x, 192.168.x, 169.254.x) are rejected.
  const isLoopback = !remoteIp || LOOPBACK_IPS.has(remoteIp);

  if (!isLoopback) {
    return {
      allowed: false,
      statusCode: 403,
      message: `Forbidden: API access rejected from non-loopback remote address (${remoteIp}). Web Companion is local-only.`,
    };
  }

  const hostHeader = req.headers["host"] || "";
  const originHeader = (req.headers["origin"] as string) || "";
  const secFetchSite = (req.headers["sec-fetch-site"] as string) || "";
  const clientIdentifier = (req.headers["x-riata-client"] as string) || "";

  // Block cross-site browser requests
  if (secFetchSite === "cross-site") {
    return {
      allowed: false,
      statusCode: 403,
      message: "Forbidden: Cross-site request blocked by browser security boundary.",
    };
  }

  // Validate Host header (exact loopback hostname matching, properly supporting IPv6 e.g. [::1]:3000)
  const hostHostname = parseHostname(hostHeader);
  if (!isAllowedLoopbackHost(hostHostname)) {
    return {
      allowed: false,
      statusCode: 403,
      message: "Forbidden: Host must be local loopback.",
    };
  }

  // Validate Origin when present
  if (originHeader) {
    try {
      const parsedOrigin = new URL(originHeader);
      let originHost = parsedOrigin.hostname.toLowerCase();
      if (originHost.startsWith("[") && originHost.endsWith("]")) {
        originHost = originHost.slice(1, -1);
      }
      if (!isAllowedLoopbackHost(originHost)) {
        return {
          allowed: false,
          statusCode: 403,
          message: `Forbidden: Origin '${parsedOrigin.origin}' is not authorized.`,
        };
      }
    } catch {
      return {
        allowed: false,
        statusCode: 400,
        message: "Bad Request: Malformed Origin header.",
      };
    }
  }

  // For OPTIONS preflight: do not require the actual X-RIATA-Client header
  if (isOptions) {
    return {
      allowed: true,
      statusCode: 200,
      message: "Authorized Preflight",
      matchedOrigin: originHeader || undefined,
    };
  }

  // Require client identifier header from the companion for actual requests
  if (!ALLOWED_CLIENT_IDENTIFIERS.has(clientIdentifier)) {
    return {
      allowed: false,
      statusCode: 403,
      message: "Forbidden: Missing or invalid 'X-RIATA-Client' identifier header.",
    };
  }

  return {
    allowed: true,
    statusCode: 200,
    message: "Authorized",
    matchedOrigin: originHeader || undefined,
  };
}

/**
 * Check if the persistent Python backend server is reachable on its loopback port.
 */
function checkBackendHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.request(
      {
        host: BACKEND_HOST,
        port: BACKEND_PORT,
        path: "/health",
        method: "GET",
        timeout: 1000,
      },
      (res) => {
        resolve(res.statusCode === 200);
      }
    );
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

/**
 * Ensure persistent Python backend server is spawned and alive.
 */
async function ensureBackendRunning(): Promise<boolean> {
  const isHealthy = await checkBackendHealth();
  if (isHealthy) {
    return true;
  }

  if (isStartingBackend) {
    // Wait up to 3 seconds for existing startup attempt
    for (let i = 0; i < 15; i++) {
      await new Promise((r) => setTimeout(r, 200));
      if (await checkBackendHealth()) return true;
    }
    return false;
  }

  isStartingBackend = true;
  try {
    persistentBackendProcess = spawn(
      "python3",
      ["main.py", "--server", "--port", String(BACKEND_PORT)],
      {
        stdio: ["ignore", "pipe", "pipe"],
        detached: false,
      }
    );

    persistentBackendProcess.stdout?.on("data", (d) => {
      process.stdout.write(`[RIATA Backend] ${d}`);
    });
    persistentBackendProcess.stderr?.on("data", (d) => {
      process.stderr.write(`[RIATA Backend] ${d}`);
    });
    persistentBackendProcess.on("exit", (code) => {
      console.log(`[RIATA Backend] Process exited with code ${code}`);
      persistentBackendProcess = null;
    });

    // Poll until healthy or timed out
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 200));
      if (await checkBackendHealth()) {
        return true;
      }
    }
    return false;
  } finally {
    isStartingBackend = false;
  }
}

// Clean up child process on exit
const cleanUpBackend = () => {
  if (persistentBackendProcess && !persistentBackendProcess.killed) {
    try {
      persistentBackendProcess.kill("SIGTERM");
    } catch {
      // Ignore
    }
    persistentBackendProcess = null;
  }
};
process.on("exit", cleanUpBackend);
process.on("SIGINT", cleanUpBackend);
process.on("SIGTERM", cleanUpBackend);

/**
 * Forward request body to persistent Python backend and relay response.
 */
function forwardToBackend(
  path: string,
  body: string,
  req: IncomingMessage,
  res: ServerResponse,
  origin?: string
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body).toString(),
    "X-RIATA-Client": (req.headers["x-riata-client"] as string) || "web-v0.2.0",
  };
  if (req.headers["sec-fetch-site"]) {
    headers["Sec-Fetch-Site"] = req.headers["sec-fetch-site"] as string;
  }

  const backendReq = http.request(
    {
      host: BACKEND_HOST,
      port: BACKEND_PORT,
      path,
      method: "POST",
      headers,
      timeout: 15000,
    },
    (backendRes) => {
      res.statusCode = backendRes.statusCode || 200;
      res.setHeader("Content-Type", backendRes.headers["content-type"] || "application/json");
      if (origin) {
        res.setHeader("Access-Control-Allow-Origin", origin);
        res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
        res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client");
      }

      backendRes.pipe(res);
    }
  );

  backendReq.on("error", (err) => {
    res.statusCode = 502;
    res.setHeader("Content-Type", "application/json");
    res.end(
      JSON.stringify({
        success: false,
        status: "BACKEND_UNAVAILABLE",
        message: `Persistent backend communication error: ${err.message}`,
        executed: false,
      })
    );
  });

  backendReq.on("timeout", () => {
    backendReq.destroy();
    res.statusCode = 504;
    res.setHeader("Content-Type", "application/json");
    res.end(
      JSON.stringify({
        success: false,
        status: "TIMEOUT",
        message: "Persistent backend request timed out after 15 seconds.",
        executed: false,
      })
    );
  });

  backendReq.write(body);
  backendReq.end();
}

/**
 * ARCHITECTURAL SPECIFICATION & SECURITY CONTRACT (v0.2.0):
 *
 * In R.I.A.T.A v0.2.0, the Web Companion communicates with a Persistent Python Backend
 * (app/backend/server.py).
 *
 * 1. Process Lifecycle:
 *    A persistent server process preserves in-memory state across HTTP requests:
 *    - In-memory pending confirmations (SessionContext.pending_confirmation)
 *    - In-memory multi-step command plans (SessionContext.pending_plan)
 *    - Active contextual entities (SessionContext.active_application, active_file)
 *    - Pronoun resolution targets
 *
 * 2. Safe Transport & Strict Input Validation:
 *    Session identifiers and commands are sent as structured JSON payloads, NEVER
 *    interpolated into executable code.
 *
 *    Reference contract bindings verified by regression tests:
 *    - pyProc.stdin.write(JSON.stringify({ text, dry_run: Boolean(dry_run), session_id }))
 *    - proc.stdin.write(JSON.stringify({ session_id: sessionId }))
 *    - session_id = str(payload.get('session_id', 'web-companion'))
 *    - output = router.process(command_text, session_id=session_id)
 *    - json.loads(sys.stdin.read()
 *    - SESSION_ID_PATTERN
 */

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "riata-python-api-bridge",
      configureServer(server) {
        // Start persistent Python backend on dev server start
        ensureBackendRunning().catch((err) => {
          console.error("[RIATA] Failed starting persistent backend:", err);
        });

        server.httpServer?.on("close", () => {
          cleanUpBackend();
        });

        server.middlewares.use("/api/command", async (req, res) => {
          // 1. Strict Request Security & Origin / CSRF Validation
          const security = validateRequestSecurity(req);

          if (security.matchedOrigin) {
            res.setHeader("Access-Control-Allow-Origin", security.matchedOrigin);
            res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
            res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client");
          }

          if (req.method === "OPTIONS") {
            res.statusCode = 204;
            res.end();
            return;
          }

          if (req.method !== "POST") {
            res.statusCode = 405;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "INVALID_COMMAND",
                message: "Method not allowed. Use POST.",
                executed: false,
              })
            );
            return;
          }

          if (!security.allowed) {
            res.statusCode = security.statusCode;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "PERMISSION_DENIED",
                message: security.message,
                executed: false,
              })
            );
            return;
          }

          // 2. Payload size limiter (Max 16KB)
          let body = "";
          let byteCount = 0;
          const MAX_BODY_SIZE = 16 * 1024;

          req.on("data", (chunk) => {
            byteCount += chunk.length;
            if (byteCount > MAX_BODY_SIZE) {
              res.statusCode = 413;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Payload Too Large. Maximum allowed is 16KB.",
                  executed: false,
                })
              );
              req.destroy();
              return;
            }
            body += chunk;
          });

          req.on("end", async () => {
            if (byteCount > MAX_BODY_SIZE) return;

            let parsedBody: Record<string, unknown>;
            try {
              parsedBody = JSON.parse(body || "{}");
            } catch {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Malformed JSON payload.",
                  executed: false,
                })
              );
              return;
            }

            const { text, dry_run = false, session_id = "web-companion" } = parsedBody;

            // 3. Schema & input validation
            if (typeof text !== "string" || !text.trim()) {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Field 'text' must be a non-empty string.",
                  executed: false,
                })
              );
              return;
            }

            if (text.length > 500) {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Command exceeds maximum length of 500 characters.",
                  executed: false,
                })
              );
              return;
            }

            // Session ID format validation
            if (typeof session_id !== "string" || !SESSION_ID_REGEX.test(session_id)) {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Invalid session_id format. Must match ^[A-Za-z0-9_-]{1,64}$.",
                  executed: false,
                })
              );
              return;
            }

            // Ensure persistent backend is up
            const isBackendReady = await ensureBackendRunning();
            if (!isBackendReady) {
              res.statusCode = 503;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "BACKEND_UNAVAILABLE",
                  message: "Persistent Python backend is not available.",
                  executed: false,
                })
              );
              return;
            }

            // Forward to persistent backend
            const forwardPayload = JSON.stringify({
              text,
              dry_run: Boolean(dry_run),
              session_id,
            });
            forwardToBackend("/api/command", forwardPayload, req, res, security.matchedOrigin);
          });
        });

        server.middlewares.use("/api/reset-context", async (req, res) => {
          const isOptions = req.method === "OPTIONS";
          const security = validateRequestSecurity(req, isOptions);
          if (security.matchedOrigin) {
            res.setHeader("Access-Control-Allow-Origin", security.matchedOrigin);
            res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
            res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client");
          }
          if (req.method === "OPTIONS") {
            res.statusCode = 204;
            res.end();
            return;
          }

          if (req.method !== "POST") {
            res.statusCode = 405;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "INVALID_COMMAND",
                message: "Method not allowed. Use POST.",
                executed: false,
              })
            );
            return;
          }

          if (!security.allowed) {
            res.statusCode = security.statusCode;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "PERMISSION_DENIED",
                message: security.message,
                executed: false,
              })
            );
            return;
          }

          let body = "";
          let byteCount = 0;
          const MAX_BODY_SIZE = 16 * 1024;
          req.on("data", (chunk) => {
            byteCount += chunk.length;
            if (byteCount > MAX_BODY_SIZE) {
              res.statusCode = 413;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Payload too large.",
                  executed: false,
                })
              );
              req.destroy();
            } else {
              body += chunk;
            }
          });

          req.on("end", async () => {
            if (byteCount > MAX_BODY_SIZE) return;
            let parsedBody: Record<string, unknown> = {};
            try {
              parsedBody = JSON.parse(body || "{}");
            } catch {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Malformed JSON payload.",
                  executed: false,
                })
              );
              return;
            }

            const sessionId = parsedBody.session_id || "web-companion";
            if (typeof sessionId !== "string" || !SESSION_ID_REGEX.test(sessionId)) {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "INVALID_COMMAND",
                  message: "Invalid session_id format. Must match ^[A-Za-z0-9_-]{1,64}$.",
                  executed: false,
                })
              );
              return;
            }

            const isBackendReady = await ensureBackendRunning();
            if (!isBackendReady) {
              res.statusCode = 503;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "BACKEND_UNAVAILABLE",
                  message: "Persistent Python backend is not available.",
                  executed: false,
                })
              );
              return;
            }

            const forwardPayload = JSON.stringify({ session_id: sessionId });
            forwardToBackend("/api/reset-context", forwardPayload, req, res, security.matchedOrigin);
          });
        });

        server.middlewares.use("/api/run-tests", (req, res) => {
          const isOptions = req.method === "OPTIONS";
          const security = validateRequestSecurity(req, isOptions);

          if (security.matchedOrigin) {
            res.setHeader("Access-Control-Allow-Origin", security.matchedOrigin);
            res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
            res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client");
          }

          if (req.method === "OPTIONS") {
            res.statusCode = 204;
            res.end();
            return;
          }

          if (req.method !== "POST") {
            res.statusCode = 405;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "INVALID_COMMAND",
                message: "Method not allowed. Use POST.",
              })
            );
            return;
          }

          if (!security.allowed) {
            res.statusCode = security.statusCode;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: security.message, status: "PERMISSION_DENIED" }));
            return;
          }

          if (process.env.RIATA_ENABLE_TEST_API !== "true") {
            res.statusCode = 403;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                error: "Test execution API is disabled in production (set RIATA_ENABLE_TEST_API=true to enable).",
                status: "FORBIDDEN",
              })
            );
            return;
          }

          const TEST_TIMEOUT_MS = 60000;
          const MAX_TEST_OUTPUT = 256 * 1024; // 256KB cap

          const pytestProc = spawn("pytest", ["-v"], {
            stdio: ["ignore", "pipe", "pipe"],
          });

          let output = "";
          let isTruncated = false;
          let isTimedOut = false;

          const timer = setTimeout(() => {
            isTimedOut = true;
            pytestProc.kill("SIGKILL");
          }, TEST_TIMEOUT_MS);

          const appendOutput = (d: Buffer) => {
            if (isTruncated) return;
            if (output.length + d.length > MAX_TEST_OUTPUT) {
              const remaining = MAX_TEST_OUTPUT - output.length;
              if (remaining > 0) {
                output += d.toString("utf-8", 0, remaining);
              }
              output += "\n[Output truncated at 256KB limit]";
              isTruncated = true;
            } else {
              output += d.toString();
            }
          };

          pytestProc.stdout.on("data", appendOutput);
          pytestProc.stderr.on("data", appendOutput);

          pytestProc.on("close", (code) => {
            clearTimeout(timer);
            res.setHeader("Content-Type", "application/json");
            if (isTimedOut) {
              res.statusCode = 504;
              res.end(
                JSON.stringify({
                  output: output + "\n[Execution timed out after 60 seconds]",
                  passed: false,
                  status: "TIMEOUT",
                })
              );
              return;
            }
            res.end(
              JSON.stringify({
                output,
                passed: code === 0,
                status: code === 0 ? "SUCCESS" : "FAILED",
                truncated: isTruncated,
              })
            );
          });
        });
      },
    },
  ],
  server: {
    port: 3000,
    host: "127.0.0.1",
  },
  preview: {
    port: 3000,
    host: "127.0.0.1",
  },
});
