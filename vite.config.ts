import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { execFile } from "child_process";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "riata-python-api-bridge",
      configureServer(server) {
        server.middlewares.use("/api/command", (req, res) => {
          if (req.method !== "POST") {
            res.statusCode = 405;
            res.end(JSON.stringify({ error: "Method not allowed" }));
            return;
          }

          let body = "";
          req.on("data", (chunk) => {
            body += chunk;
          });

          req.on("end", () => {
            try {
              const { text, dry_run = false } = JSON.parse(body || "{}");
              if (!text) {
                res.setHeader("Content-Type", "application/json");
                res.end(JSON.stringify({ error: "Empty command" }));
                return;
              }

              const pyCode = `
import json, sys
from app.engine.router import get_intent_router
from app.core.config import get_config
from app.core.logger import LOG_BUFFER

cfg = get_config()
if ${dry_run ? "True" : "False"}:
    cfg.dry_run = True

router = get_intent_router()
output = router.process(${JSON.stringify(text)})

data = {
    "response": output.response_text,
    "intent": output.intent.to_dict() if output.intent else None,
    "direction": output.direction,
    "is_exit": output.is_exit,
    "logs": list(LOG_BUFFER)[-15:]
}
print("---RIATA_JSON_START---")
print(json.dumps(data))
print("---RIATA_JSON_END---")
`;

              execFile("python3", ["-c", pyCode], (error, stdout, stderr) => {
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
                      error: stderr || error?.message || "Execution error",
                    })
                  );
                }
              });
            } catch (err: any) {
              res.statusCode = 400;
              res.setHeader("Content-Type", "application/json");
              res.end(JSON.stringify({ error: err.message }));
            }
          });
        });

        server.middlewares.use("/api/run-tests", (req, res) => {
          execFile("pytest", ["-v"], (error, stdout, stderr) => {
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                output: stdout + (stderr ? "\n" + stderr : ""),
                passed: !error,
              })
            );
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
