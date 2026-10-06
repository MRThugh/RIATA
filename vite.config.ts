import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { spawn } from "child_process";

// Local loopback allowed origins and hosts
const ALLOWED_LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "127.0.0.1:3000", "localhost:3000"]);

function isLocalOrigin(originHeader?: string, hostHeader?: string): boolean {
  if (hostHeader && ALLOWED_LOCAL_HOSTS.has(hostHeader.toLowerCase())) {
    // Standard local request
  }
  if (!originHeader) {
    return true; // Direct same-origin or non-browser local request
  }
  try {
    const parsed = new URL(originHeader);
    return parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "riata-python-api-bridge",
      configureServer(server) {
        server.middlewares.use("/api/command", (req, res) => {
          // 1. Origin / Host access validation
          const hostHeader = req.headers["host"] || "";
          const originHeader = (req.headers["origin"] as string) || "";

          // Set restricted CORS header to local origin if valid, never '*'
          if (originHeader && isLocalOrigin(originHeader, hostHeader)) {
            res.setHeader("Access-Control-Allow-Origin", originHeader);
            res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
            res.setHeader("Access-Control-Allow-Headers", "Content-Type");
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

          // Origin check
          if (!isLocalOrigin(originHeader, hostHeader)) {
            res.statusCode = 403;
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                success: false,
                status: "PERMISSION_DENIED",
                message: "Forbidden: API is restricted to local loopback.",
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
            } catch (err) {
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

            // 4. Safe Python execution passing data over stdin JSON
            const pyScript = `
import json, sys
from app.engine.router import get_intent_router
from app.core.config import get_config
from app.core.logger import LOG_BUFFER

try:
    payload = json.loads(sys.stdin.read() or '{}')
    command_text = payload.get('text', '')
    dry_run = bool(payload.get('dry_run', False))

    cfg = get_config()
    if dry_run:
        cfg.dry_run = True

    router = get_intent_router()
    output = router.process(command_text)

    result_dict = output.result.to_dict() if output.result else {
        "success": False,
        "executed": False,
        "status": "UNKNOWN",
        "message": output.response_text
    }

    data = {
        "success": output.result.success if output.result else False,
        "executed": output.result.executed if output.result else False,
        "status": output.result.status if output.result else "SUCCESS",
        "response": output.response_text,
        "intent": output.intent.to_dict() if output.intent else None,
        "result": result_dict,
        "direction": output.direction,
        "is_exit": output.is_exit,
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

            pyProc.stdout.on("data", (data) => {
              stdout += data.toString();
            });

            pyProc.stderr.on("data", (data) => {
              stderr += data.toString();
            });

            pyProc.on("close", (code) => {
              res.setHeader("Content-Type", "application/json");
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
          const originHeader = (req.headers["origin"] as string) || "";
          const hostHeader = req.headers["host"] || "";

          if (!isLocalOrigin(originHeader, hostHeader)) {
            res.statusCode = 403;
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify({ error: "Forbidden: Local access only." }));
            return;
          }

          if (originHeader) {
            res.setHeader("Access-Control-Allow-Origin", originHeader);
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
      },
    },
  ],
  server: {
    port: 3000,
    // Bound strictly to local loopback by default to prevent unauthorized network access
    host: process.env.RIATA_HOST || "127.0.0.1",
  },
});
