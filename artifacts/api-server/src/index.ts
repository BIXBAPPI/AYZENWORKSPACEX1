import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import app from "./app";
import { logger } from "./lib/logger";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

// ─── Spawn Python FastAPI in production ──────────────────────────────────────
if (process.env["NODE_ENV"] === "production") {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  // In the deployment VM the repo root is /home/runner/workspace
  const root = path.resolve(__dirname, "../../..");
  const python = path.join(root, ".venv", "bin", "python");

  function spawnPython() {
    const py = spawn(
      python,
      ["-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
      {
        cwd: root,
        env: { ...process.env, PYTHONPATH: root },
        stdio: "pipe",
      },
    );

    py.stdout.on("data", (chunk: Buffer) =>
      chunk.toString().split("\n").filter(Boolean).forEach((l) => logger.info({ src: "python" }, l)),
    );
    py.stderr.on("data", (chunk: Buffer) =>
      chunk.toString().split("\n").filter(Boolean).forEach((l) => logger.info({ src: "python" }, l)),
    );

    py.on("exit", (code, signal) => {
      logger.warn({ code, signal }, "Python process exited — restarting in 2 s");
      setTimeout(spawnPython, 2000);
    });

    py.on("error", (err) => {
      logger.error({ err }, "Failed to start Python process");
    });

    logger.info({ python, cwd: root }, "Starting Python FastAPI");
  }

  spawnPython();
}

// ─── Start Express ────────────────────────────────────────────────────────────
app.listen(port, (err) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    process.exit(1);
  }

  logger.info({ port }, "Server listening");
});
