import { Router } from "express";

const router = Router();
const PYTHON_API = "http://localhost:8000/api/v1";

router.use(async (req, res) => {
  try {
    const url = `${PYTHON_API}/auth${req.path}`;
    const response = await fetch(url, {
      method: req.method,
      headers: { "Content-Type": "application/json" },
      body: ["GET","HEAD"].includes(req.method) ? undefined : JSON.stringify(req.body),
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (e) {
    res.status(502).json({ error: "python_api_unavailable" });
  }
});

export default router;
