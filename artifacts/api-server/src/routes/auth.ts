import { Router } from "express";
import type { Request, Response } from "express";

const router = Router();
const PYTHON = "http://localhost:8000/api/v1";

async function proxyAuth(req: Request, res: Response): Promise<void> {
  try {
    const r = await fetch(`${PYTHON}/auth${req.path}`, {
      method: req.method,
      headers: { "Content-Type": "application/json" },
      body: ["GET", "HEAD"].includes(req.method) ? undefined : JSON.stringify(req.body),
    });
    const data = await r.json();
    res.status(r.status).json(data);
  } catch {
    res.status(502).json({ error: "python_api_unavailable" });
  }
}

router.post("/login", proxyAuth);
router.post("/register", proxyAuth);
router.post("/logout", proxyAuth);
router.get("/me", proxyAuth);

export default router;
