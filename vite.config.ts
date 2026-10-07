import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { spawn } from "child_process";
import { IncomingMessage } from "http";

// Client identifier token used to distinguish requests from the bundled companion
const ALLOWED_CLIENT_IDENTIFIERS = new Set(["web-v0.1.1", "web-v0.2.0"]);

// Allowed loopback hostnames and remote IP addresses
const LOOPBACK_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1", "[::1]", "0.0.0.0"]);
const LOOPBACK_IPS = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1", "0.0.0.0"]);

interface SecurityCheckResult {
  allowed: boolean;
  statusCode: number;
  message: string;
  matchedOrigin?: string;
}

function isAllowedHostOrOrigin(target: string): boolean {
  if (!target) return true;
  if (LOOPBACK_HOSTNAMES.has(target)) return true;
  if (
    target.endsWith(".run.app") ||
    target.endsWith(".aistudio.google") ||
    target.endsWith(".google.internal") ||
    target.includes("localhost") ||
    target.includes("127.0.0.1")
  ) {
    return true;
  }
  return false;
}

function validateRequestSecurity(req: IncomingMessage): SecurityCheckResult {
  const remoteIp = req.socket?.remoteAddress || "";
  const isPrivateOrLoopback =
    !remoteIp ||
    LOOPBACK_IPS.has(remoteIp) ||
    remoteIp.startsWith("10.") ||
    remoteIp.startsWith("172.") ||
    remoteIp.startsWith("192.168.") ||
    remoteIp.startsWith("169.254.") ||
    remoteIp.endsWith("127.0.0.1");

  if (!isPrivateOrLoopback) {
    return {
      allowed: false,
      statusCode: 403,
      message: `Forbidden: API access rejected from non-local remote address (${remoteIp}).`,
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

  // Validate Host header
  if (!isAllowedHostOrOrigin(hostHeader)) {
    return {
      allowed: false,
      statusCode: 403,
      message: "Forbidden: Host must be local loopback or authorized preview domain.",
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

            const { text, dry_run = false } = parsedBody;

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
          if (!security.allowed) {
            res.statusCode = security.statusCode;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: security.message }));
            return;
          }

          let body = "";
          req.on("data", (chunk) => {
            body += chunk;
          });
          req.on("end", () => {
            let sessionId = "web-companion";
            try {
              const p = JSON.parse(body || "{}");
              if (p.session_id) sessionId = p.session_id;
            } catch {}

            const pyScript = `
import json
from app.core.context.manager import get_context_manager
cm = get_context_manager()
cm.reset_session("${sessionId}")
print(json.dumps({"success": True, "message": "Context reset successfully"}))
`;
            const proc = spawn("python3", ["-c", pyScript]);
            let out = "";
            proc.stdout.on("data", (d) => {
              out += d.toString();
            });
            proc.on("close", () => {
              res.setHeader("Content-Type", "application/json");
              res.end(out || JSON.stringify({ success: true, message: "Context reset" }));
            });
          });
        });
      },
    },
  ],
  server: {
    port: 3000,
    host: "0.0.0.0",
  },
});
