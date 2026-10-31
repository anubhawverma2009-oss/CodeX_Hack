import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import fs from "fs";
import { spawn, ChildProcess } from "child_process";

const UPLOADS_DIR = path.resolve(".", "uploads");
if (!fs.existsSync(UPLOADS_DIR)) {
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

const DEFAULT_PDF_PATH = path.resolve(".", "public", "assets", "aistudio", "report_A_90150542.pdf");

class PythonBridge {
  private daemon: ChildProcess | null = null;
  private pendingCallbacks: Array<(data: any) => void> = [];
  public activePdfPath: string = DEFAULT_PDF_PATH;
  public activeFilename: string = "report_A.pdf (Default Report)";
  public numPages: number = 272;
  public reportYear: number = 2023;
  public ocrStatus: string = "active";
  public isReady: boolean = false;

  constructor() {
    this.startDaemon();
  }

  public startDaemon() {
    if (this.daemon) {
      try {
        this.daemon.kill();
      } catch (e) {}
    }

    this.daemon = spawn("python3", ["solution/server_daemon.py"], {
      stdio: ["pipe", "pipe", "inherit"],
    });

    let buffer = "";
    this.daemon.stdout?.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const parsed = JSON.parse(line.trim());
          const cb = this.pendingCallbacks.shift();
          if (cb) cb(parsed);
        } catch (err) {
          console.error("Failed to parse daemon response:", line, err);
        }
      }
    });

    this.daemon.on("close", (code) => {
      console.warn(`Python daemon exited with code ${code}. Restarting...`);
      this.isReady = false;
      setTimeout(() => this.startDaemon(), 1000);
    });

    setTimeout(() => {
      this.sendCommand({ action: "status" }, (res) => {
        if (res.status === "ok") {
          this.numPages = res.num_pages || 272;
          this.reportYear = res.report_year || 2023;
          this.isReady = true;
          console.log(`Python Daemon ready. Pages: ${this.numPages}, Year: ${this.reportYear}`);
        }
      });
    }, 1500);
  }

  public sendCommand(cmd: any, callback: (data: any) => void) {
    if (!this.daemon || !this.daemon.stdin || !this.daemon.stdin.writable) {
      callback({ status: "error", message: "Daemon not writable" });
      return;
    }
    this.pendingCallbacks.push(callback);
    this.daemon.stdin.write(JSON.stringify(cmd) + "\n");
  }

  public loadPdf(pdfPath: string, filename: string): Promise<any> {
    return new Promise((resolve) => {
      this.sendCommand({ action: "load_pdf", pdf_path: pdfPath }, (res) => {
        if (res.status === "ok") {
          this.activePdfPath = pdfPath;
          this.activeFilename = filename;
          this.numPages = res.num_pages;
          this.reportYear = res.report_year;
          this.ocrStatus = res.ocr_status || "active";
          this.isReady = true;
        }
        resolve(res);
      });
    });
  }

  public query(question: string, id: string = "custom"): Promise<any> {
    return new Promise((resolve) => {
      this.sendCommand({ action: "query", question, id }, (res) => {
        resolve(res);
      });
    });
  }

  public getPage(pageNum: number): Promise<any> {
    return new Promise((resolve) => {
      this.sendCommand({ action: "get_page", page: pageNum }, (res) => {
        resolve(res);
      });
    });
  }
}

async function startServer() {
  const app = express();
  const PORT = 3000;
  const bridge = new PythonBridge();

  app.use(express.json({ limit: "50mb" }));
  app.use("/downloads", express.static(path.resolve(".", "public", "downloads")));

  // API 1: Get Active PDF Status
  app.get("/api/active-pdf", (req, res) => {
    res.json({
      filename: bridge.activeFilename,
      path: bridge.activePdfPath,
      numPages: bridge.numPages,
      reportYear: bridge.reportYear,
      ocrStatus: bridge.ocrStatus,
      isDefault: bridge.activePdfPath === DEFAULT_PDF_PATH,
      isReady: bridge.isReady,
    });
  });

  // API 2: Upload PDF with Safe Streaming (Task 5)
  app.post("/api/upload-pdf", async (req, res) => {
    const rawFilename = (req.query.filename as string) || "uploaded_report.pdf";
    const cleanName = path.basename(rawFilename).replace(/[^a-zA-Z0-9._-]/g, "_");
    const targetPath = path.join(UPLOADS_DIR, `${Date.now()}_${cleanName}`);

    const writeStream = fs.createWriteStream(targetPath);
    let totalBytes = 0;
    let uploadAborted = false;

    req.on("data", (chunk) => {
      totalBytes += chunk.length;
      if (totalBytes > 250 * 1024 * 1024) {
        uploadAborted = true;
        req.destroy();
        writeStream.close();
        if (fs.existsSync(targetPath)) {
          try { fs.unlinkSync(targetPath); } catch (e) {}
        }
        return res.status(413).json({ error: "Upload size exceeds 250MB limit." });
      }
    });

    try {
      req.pipe(writeStream);

      await new Promise((resolve, reject) => {
        writeStream.on("finish", () => resolve(true));
        writeStream.on("error", reject);
      });

      if (uploadAborted) return;

      if (totalBytes < 10) {
        if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath);
        return res.status(400).json({ error: "Empty or invalid file uploaded." });
      }

      // Validate PDF header magic bytes (%PDF)
      const fd = fs.openSync(targetPath, "r");
      const headerBuf = Buffer.alloc(5);
      fs.readSync(fd, headerBuf, 0, 5, 0);
      fs.closeSync(fd);

      if (!headerBuf.toString("ascii").startsWith("%PDF")) {
        if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath);
        return res.status(400).json({ error: "Uploaded file is not a valid PDF document (missing %PDF signature)." });
      }

      const result = await bridge.loadPdf(targetPath, cleanName);
      if (result.status === "ok") {
        res.json({
          success: true,
          filename: cleanName,
          numPages: result.num_pages,
          reportYear: result.report_year,
          ocrStatus: result.ocr_status,
          tablesIndexed: result.tables_indexed,
        });
      } else {
        if (fs.existsSync(targetPath)) fs.unlinkSync(targetPath);
        res.status(500).json({ error: result.message || "Failed to index uploaded PDF" });
      }
    } catch (err: any) {
      console.error("Upload stream error:", err);
      if (fs.existsSync(targetPath)) {
        try { fs.unlinkSync(targetPath); } catch (e) {}
      }
      res.status(500).json({ error: err.message || "Upload stream failed" });
    }
  });

  // API 3: Reset to Default Practice Report
  app.post("/api/reset-pdf", async (req, res) => {
    try {
      const result = await bridge.loadPdf(DEFAULT_PDF_PATH, "report_A.pdf (Default Report)");
      res.json({
        success: true,
        filename: bridge.activeFilename,
        numPages: bridge.numPages,
        reportYear: bridge.reportYear,
        ocrStatus: bridge.ocrStatus,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // API 4: List Practice Questions
  app.get("/api/questions", (req, res) => {
    try {
      const qPath = path.resolve(".", "data", "questions_with_answers.jsonl");
      if (!fs.existsSync(qPath)) {
        return res.status(404).json({ error: "Questions file not found" });
      }
      const lines = fs.readFileSync(qPath, "utf-8").split("\n").filter((l) => l.trim());
      const questions = lines.map((l) => JSON.parse(l));
      res.json({ questions, count: questions.length });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // API 5: Query Single Question
  app.post("/api/ask", async (req, res) => {
    try {
      const { question, id } = req.body;
      if (!question) {
        return res.status(400).json({ error: "question string is required" });
      }

      const qId = id || "custom";
      const daemonResponse = await bridge.query(question, qId);

      if (daemonResponse.status === "ok") {
        res.json(daemonResponse.result);
      } else {
        res.status(500).json({ error: daemonResponse.message || "Query failed" });
      }
    } catch (err: any) {
      console.error("Query API error:", err);
      res.status(500).json({ error: err.message || "Execution error" });
    }
  });

  // API 6: Get Benchmark Scorecard (Task 3: Transparency labeling)
  app.get("/api/benchmark", (req, res) => {
    try {
      const qPath = path.resolve(".", "data", "questions_with_answers.jsonl");
      const predPath = path.resolve(".", "data", "predictions.jsonl");

      if (!fs.existsSync(qPath) || !fs.existsSync(predPath)) {
        return res.status(404).json({ error: "Benchmark data not ready" });
      }

      const qLines = fs.readFileSync(qPath, "utf-8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
      const pLines = fs.readFileSync(predPath, "utf-8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));

      const predMap = new Map<string, any>();
      pLines.forEach((p) => predMap.set(p.id, p));

      let exactMatchCount = 0;
      let pageMatchCount = 0;

      const detailed = qLines.map((q) => {
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
          isPageMatch,
        };
      });

      res.json({
        total: qLines.length,
        exactMatchCount,
        exactMatchPct: ((exactMatchCount / qLines.length) * 100).toFixed(2),
        pageMatchCount,
        pageMatchPct: ((pageMatchCount / qLines.length) * 100).toFixed(2),
        source: "Precomputed Practice Benchmark (predictions.jsonl)",
        isPrecomputed: true,
        items: detailed,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // API 7: Page Inspection
  app.get("/api/page/:num", async (req, res) => {
    try {
      const pageNum = parseInt(req.params.num, 10);
      if (isNaN(pageNum) || pageNum < 1 || pageNum > bridge.numPages) {
        return res.status(400).json({
          error: `Invalid page number ${pageNum}. Document contains ${bridge.numPages} pages.`,
        });
      }

      const pageRes = await bridge.getPage(pageNum);
      if (pageRes.status === "ok") {
        res.json({ page: pageNum, totalPages: bridge.numPages, text: pageRes.text });
      } else {
        res.status(500).json({ error: pageRes.message });
      }
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(".", "dist")));
    app.get("*", (req, res) => {
      res.sendFile(path.resolve(".", "dist", "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`P5 Report Navigator server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
});
