import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import fs from "fs";
import { execFile, exec } from "child_process";
import { promisify } from "util";

const execPromise = promisify(exec);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // Static downloads folder
  app.use("/downloads", express.static(path.resolve(".", "public", "downloads")));

  // API 1: List Practice Questions
  app.get("/api/questions", (req, res) => {
    try {
      const qPath = path.resolve(".", "data", "questions_with_answers.jsonl");
      if (!fs.existsSync(qPath)) {
        return res.status(404).json({ error: "Questions file not found" });
      }
      const lines = fs.readFileSync(qPath, "utf-8").split("\n").filter(l => l.trim());
      const questions = lines.map(l => JSON.parse(l));
      res.json({ questions, count: questions.length });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // API 2: Query Single Question
  app.post("/api/ask", async (req, res) => {
    try {
      const { question, id } = req.body;
      if (!question) {
        return res.status(400).json({ error: "question string is required" });
      }

      // Safe command execution
      const sanitizedQ = question.replace(/"/g, '\\"');
      const cmd = `python3 solution/query.py "${sanitizedQ}"`;
      const { stdout } = await execPromise(cmd, { timeout: 15000 });
      
      const parsed = JSON.parse(stdout.trim());
      if (id) {
        parsed.id = id;
      }
      res.json(parsed);
    } catch (err: any) {
      console.error("Query error:", err);
      res.status(500).json({ error: err.message || "Execution error" });
    }
  });

  // API 3: Get Benchmark Results
  app.get("/api/benchmark", (req, res) => {
    try {
      const qPath = path.resolve(".", "data", "questions_with_answers.jsonl");
      const predPath = path.resolve(".", "data", "predictions.jsonl");

      if (!fs.existsSync(qPath) || !fs.existsSync(predPath)) {
        return res.status(404).json({ error: "Benchmark data not ready" });
      }

      const qLines = fs.readFileSync(qPath, "utf-8").split("\n").filter(l => l.trim()).map(l => JSON.parse(l));
      const pLines = fs.readFileSync(predPath, "utf-8").split("\n").filter(l => l.trim()).map(l => JSON.parse(l));

      const predMap = new Map<string, any>();
      pLines.forEach(p => predMap.set(p.id, p));

      let exactMatchCount = 0;
      let pageMatchCount = 0;

      const detailed = qLines.map(q => {
        const pred = predMap.get(q.id) || { answer: "NOT_FOUND", page: null, confidence: 0 };
        const isAnsMatch = String(pred.answer).trim() === String(q.answer).trim();
        const goldPgs: number[] = q.gold_pages || [];
        const isPageMatch = goldPgs.length > 0 ? goldPgs.includes(pred.page) : pred.page === null;

        if (isAnsMatch) exactMatchCount++;
        if (isPageMatch) pageMatchCount++;

        return {
          id: q.id,
          question: q.question,
          qtype: q.qtype,
          goldAnswer: q.answer,
          goldPages: q.gold_pages,
          predAnswer: pred.answer,
          predPage: pred.page,
          confidence: pred.confidence,
          isAnsMatch,
          isPageMatch
        };
      });

      res.json({
        total: qLines.length,
        exactMatchCount,
        exactMatchPct: ((exactMatchCount / qLines.length) * 100).toFixed(2),
        pageMatchCount,
        pageMatchPct: ((pageMatchCount / qLines.length) * 100).toFixed(2),
        items: detailed
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // API 4: Page Content Snippet
  app.get("/api/page/:num", async (req, res) => {
    try {
      const pageNum = parseInt(req.params.num, 10);
      if (isNaN(pageNum) || pageNum < 1 || pageNum > 272) {
        return res.status(400).json({ error: "Invalid page number" });
      }

      const cmd = `python3 -c "import pypdf; r=pypdf.PdfReader('public/assets/aistudio/report_A_90150542.pdf'); print(r.pages[${pageNum - 1}].extract_text() or '')"`;
      const { stdout } = await execPromise(cmd, { timeout: 10000 });
      res.json({ page: pageNum, text: stdout });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Vite development middleware
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Production static serving
    app.use(express.static(path.resolve(".", "dist")));
    app.get("*", (req, res) => {
      res.sendFile(path.resolve(".", "dist", "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`P5 Report Navigator server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch(err => {
  console.error("Failed to start server:", err);
});
