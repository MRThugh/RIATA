import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { spawn } from "child_process";
import { IncomingMessage } from "http";

// Client identifier token used to distinguish requests from the bundled companion
// Note: This is a client identification header for companion routing, not an authentication credential.
const ALLOWED_CLIENT_IDENTIFIERS = new Set(["web-v0.1.1", "web-v0.2.0"]);

// Strict loopback hostnames and remote IP addresses (0.0.0.0 and LAN ranges explicitly removed)
const LOOPBACK_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
const LOOPBACK_IPS = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1"]);

// Canonical session ID format validator (1 to 64 alphanumeric characters, underscores, and hyphens)
const SESSION_ID_REGEX = /^[A-Za-z0-9_-]{1,64}$/;

interface SecurityCheckResult {
  allowed: boolean;
  statusCode: number;
  message: string;
  matchedOrigin?: string;
}

function isAllowedHostOrOrigin(target: string): boolean {
  if (!target) return true;
  // Exact match against loopback hostnames
  if (LOOPBACK_HOSTNAMES.has(target)) return true;

  // Cloud/preview host exceptions are disabled by default.
  // Only permit preview hosts when explicitly opted-in via environment variable.
  if (process.env.RIATA_ALLOW_PREVIEW_HOSTS === "true") {
    if (
      target.endsWith(".run.app") ||
      target.endsWith(".aistudio.google") ||
      target.endsWith(".google.internal")
    ) {
      return true;
    }
  }
  return false;
}

function validateRequestSecurity(req: IncomingMessage): SecurityCheckResult {
  const remoteIp = req.socket?.remoteAddress || "";
  // Strictly permit loopback only. Private LAN addresses (10.x, 172.x, 192.168.x, 169.254.x) are rejected.
  const isLoopback = !remoteIp || LOOPBACK_IPS.has(remoteIp);
  const isPreviewOptIn = process.env.RIATA_ALLOW_PREVIEW_HOSTS === "true";

  if (!isLoopback && !isPreviewOptIn) {
    return {
      allowed: false,
      statusCode: 403,
      message: `Forbidden: API access rejected from non-loopback remote address (${remoteIp}). Web Companion is local-only.`,
    };
  }

  const hostHeader = (req.headers["host"] || "").split(":")[0].toLowerCase();
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

  // Validate Host header (exact loopback hostname matching)
  if (!isAllowedHostOrOrigin(hostHeader)) {
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
      const originHost = parsedOrigin.hostname.toLowerCase();
      if (!isAllowedHostOrOrigin(originHost)) {
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

  // Require client identifier header from the companion
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
            pyProc.stdin.write(JSON.stringify({ text, dry_run: Boolean(dry_run) }));
            pyProc.stdin.end();
          });
        });

        server.middlewares.use("/api/run-tests", (req, res) => {
          const security = validateRequestSecurity(req);

          if (security.matchedOrigin) {
            res.setHeader("Access-Control-Allow-Origin", security.matchedOrigin);
            res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
            res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client");
          }

          if (req.method === "OPTIONS") {
            res.statusCode = 204;
            res.end();
            return;
          }

          if (!security.allowed) {
            res.statusCode = security.statusCode;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: security.message }));
            return;
          }

          const pytestProc = spawn("pytest", ["-v"], {
            stdio: ["ignore", "pipe", "pipe"],
          });

          let output = "";
          pytestProc.stdout.on("data", (d) => {
            output += d.toString();
          });
          pytestProc.stderr.on("data", (d) => {
            output += d.toString();
          });

          pytestProc.on("close", (code) => {
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                output,
                passed: code === 0,
                status: code === 0 ? "SUCCESS" : "FAILED",
              })
            );
          });
        });

        server.middlewares.use("/api/reset-context", (req, res) => {
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
from app.core.context.manager import get_context_manager

SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

try:
    payload = json.loads(sys.stdin.read() or '{}')
    session_id = str(payload.get('session_id', 'web-companion'))
    if not SESSION_ID_PATTERN.match(session_id):
        print(json.dumps({"success": False, "status": "INVALID_COMMAND", "message": "Invalid session_id"}))
        sys.exit(0)

    cm = get_context_manager()
    cm.reset_session(session_id)
    print(json.dumps({"success": True, "status": "SUCCESS", "message": "Context reset successfully"}))
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
