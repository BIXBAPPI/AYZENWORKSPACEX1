import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import { createProxyMiddleware } from "http-proxy-middleware";
import path from "path";
import { fileURLToPath } from "url";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// ─── HEALTHCHECK — must respond 200 immediately, before all middleware ─────────
app.get("/api", (_req, res) => {
  res.status(200).json({ status: "ok", service: "ayzen-workspace" });
});
app.get("/api/healthz", (_req, res) => {
  res.status(200).json({ status: "ok" });
});

// ─── LOGGING ──────────────────────────────────────────────────────────────────
app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return { id: req.id, method: req.method, url: req.url?.split("?")[0] };
      },
      res(res) {
        return { statusCode: res.statusCode };
      },
    },
  }),
);

app.use(cors({ origin: true, credentials: true }));

// ─── PROXY /api/v1/* → FastAPI (MUST be before body parsers) ─────────────────
// express.json() consumes the request body stream; if it runs first the proxy
// receives an empty body and the Python API hangs on POST requests.
app.use(
  createProxyMiddleware({
    target: "http://localhost:8000",
    changeOrigin: false,
    pathFilter: "/api/v1",
    on: {
      error(err, _req, res) {
        logger.error({ err }, "Python API proxy error");
        if (typeof (res as express.Response).status === "function") {
          (res as express.Response)
            .status(502)
            .json({ error: "python_api_unavailable" });
        }
      },
    },
  }),
);

// ─── BODY PARSERS (only reached for non-/api/v1 routes) ───────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ─── LOCAL NODE ROUTES ─────────────────────────────────────────────────────────
app.use("/api", router);

// ─── SERVE REACT DASHBOARD IN PRODUCTION ──────────────────────────────────────
if (process.env.NODE_ENV === "production") {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const staticDir = path.resolve(__dirname, "../../dashboard/dist/public");
  app.use(express.static(staticDir));
  app.get("*", (_req, res) => {
    res.sendFile(path.join(staticDir, "index.html"));
  });
}

export default app;
