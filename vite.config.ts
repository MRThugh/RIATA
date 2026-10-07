import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { spawn } from "child_process";
import { IncomingMessage } from "http";

// Client identifier header used by the companion to route requests.
// NOTE: This header is a client identifier, NOT an authentication mechanism.
const ALLOWED_CLIENT_IDENTIFIERS = new Set(["web-v0.2.0"]);

// Strict loopback hostnames and remote IP addresses (0.0.0.0 and LAN ranges explicitly removed)
const LOOPBACK_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1"]);
const LOOPBACK_IPS = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

// Canonical session ID format validator (1 to 64 alphanumeric characters, underscores, and hyphens)
const SESSION_ID_REGEX = /^[A-Za-z0-9_-]{1,64}$/;

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

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "riata-python-api-bridge",
      configureServer(server) {
        server.middlewares.use("/api/command", (req, res) => {
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

          req.on("end", () => {
            if (byteCount > MAX_BODY_SIZE) return;

            let parsedBody: any;
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

            // 4. Safe Python execution passing data over stdin JSON with execution timeout
            const pyScript = `
import json, sys
from app.engine.router import get_intent_router
from app.core.config import get_config
from app.core.logger import LOG_BUFFER

try:
    payload = json.loads(sys.stdin.read() or '{}')
    command_text = payload.get('text', '')
    dry_run = bool(payload.get('dry_run', False))
    session_id = str(payload.get('session_id', 'web-companion'))

    cfg = get_config()
    if dry_run:
        cfg.dry_run = True

    router = get_intent_router()
    output = router.process(command_text, session_id=session_id)

    result_dict = output.result.to_dict() if output.result else {
        "success": False,
        "executed": False,
        "status": "UNKNOWN",
        "message": output.response_text
    }

    session_ctx = router.context_manager.get_session(session_id)
    ctx_dict = session_ctx.to_dict() if session_ctx else {}

    data = {
        "success": output.result.success if output.result else False,
        "executed": output.result.executed if output.result else False,
        "status": output.result.status if output.result else "SUCCESS",
        "response": output.response_text,
        "intent": output.intent.to_dict() if output.intent else None,
        "result": result_dict,
        "direction": output.direction,
        "is_exit": output.is_exit,
        "plan": output.plan.to_dict() if output.plan else None,
        "context": ctx_dict,
        "session_id": session_id,
        "logs": list(LOG_BUFFER)[-15:]
    }
    print("---RIATA_JSON_START---")
    print(json.dumps(data))
    print("---RIATA_JSON_END---")
except Exception as e:
    err_data = {
        "success": False,
        "executed": False,
        "status": "EXECUTION_ERROR",
        "message": str(e)
    }
    print("---RIATA_JSON_START---")
    print(json.dumps(err_data))
    print("---RIATA_JSON_END---")
`;

            const pyProc = spawn("python3", ["-c", pyScript], {
              stdio: ["pipe", "pipe", "pipe"],
            });

            let stdout = "";
            let stderr = "";
            let isTimedOut = false;

            const timer = setTimeout(() => {
              isTimedOut = true;
              pyProc.kill("SIGKILL");
            }, 15000);

            pyProc.stdout.on("data", (data) => {
              stdout += data.toString();
            });

            pyProc.stderr.on("data", (data) => {
              stderr += data.toString();
            });

            pyProc.on("close", (code) => {
              clearTimeout(timer);
              res.setHeader("Content-Type", "application/json");

              if (isTimedOut) {
                res.statusCode = 504;
                res.end(
                  JSON.stringify({
                    success: false,
                    executed: false,
                    status: "TIMEOUT",
                    message: "Intent processing timed out after 15 seconds.",
                  })
                );
                return;
              }

              if (stdout.includes("---RIATA_JSON_START---")) {
                const jsonStr = stdout
                  .split("---RIATA_JSON_START---")[1]
                  .split("---RIATA_JSON_END---")[0]
                  .trim();
                res.end(jsonStr);
              } else {
                res.statusCode = 500;
                res.end(
                  JSON.stringify({
                    success: false,
                    executed: false,
                    status: "EXECUTION_ERROR",
                    message: "Internal Python engine error.",
                    error: stderr || `Process exited with code ${code}`,
                  })
                );
              }
            });

            // Send payload safely via stdin JSON
            pyProc.stdin.write(JSON.stringify({ text, dry_run: Boolean(dry_run), session_id }));
            pyProc.stdin.end();
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

          // Section 11: Explicit development-only gate (RIATA_ENABLE_TEST_API=true)
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

        server.middlewares.use("/api/reset-context", (req, res) => {
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
          req.on("end", () => {
            if (byteCount > MAX_BODY_SIZE) return;
            let parsedBody: any = {};
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

            const pyScript = `
import json, sys, re
from app.engine.router import get_intent_router

SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

try:
    payload = json.loads(sys.stdin.read() or '{}')
    session_id = str(payload.get('session_id', 'web-companion'))
    if not SESSION_ID_PATTERN.match(session_id):
        print(json.dumps({"success": False, "status": "INVALID_COMMAND", "message": "Invalid session_id"}))
        sys.exit(0)

    router = get_intent_router()
    session_ctx = router.context_manager.get_session(session_id)
    if session_ctx:
        session_ctx.clear()
    router.context_manager.reset(session_id)
    router.reset_context()
    print(json.dumps({"success": True, "status": "SUCCESS", "message": "Context reset successfully", "session_id": session_id}))
except Exception as e:
    print(json.dumps({"success": False, "status": "FAILED", "message": str(e)}))
`;
            const proc = spawn("python3", ["-c", pyScript]);
            let stdoutData = "";
            let stderrData = "";

            const timer = setTimeout(() => {
              proc.kill("SIGKILL");
              res.statusCode = 504;
              res.setHeader("Content-Type", "application/json");
              res.end(
                JSON.stringify({
                  success: false,
                  status: "FAILED",
                  message: "Context reset execution timed out.",
                  executed: false,
                })
              );
            }, 10000);

            proc.stdout.on("data", (d) => {
              stdoutData += d.toString();
            });
            proc.stderr.on("data", (d) => {
              stderrData += d.toString();
            });

            proc.on("close", (code) => {
              clearTimeout(timer);
              res.setHeader("Content-Type", "application/json");
              if (stdoutData.trim()) {
                res.end(stdoutData.trim());
              } else {
                res.statusCode = code === 0 ? 200 : 500;
                res.end(
                  JSON.stringify({
                    success: false,
                    status: "FAILED",
                    message: stderrData || "Context reset process failed",
                  })
                );
              }
            });

            // Write stdin data safely without string interpolation
            proc.stdin.write(JSON.stringify({ session_id: sessionId }));
            proc.stdin.end();
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
