# BloodParser - AI-Powered Medical Report Dashboard

BloodParser is a full-stack medical analytics dashboard that processes lab reports through an AI-powered OCR and analysis pipeline. Users can upload PDFs or images of blood test results, and the system automatically extracts, categorizes, and visualizes biomarkers in an interactive interface.

The primary pipeline uses **GLM-OCR** for document parsing, followed by **Gemini** for structured extraction. For quick setup and free-tier usage, the app also supports a direct **Gemini Vision** fallback path.

---

## Demo

<video src="./docs/media/demo.mp4" controls width="100%"></video>

- Live demo: [blood-parser.vercel.app](https://blood-parser.vercel.app/)

Sample report inputs available in this repo:

| CBC                                            | CMP                                            | Thyroid                                                        |
| ---------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------- |
| ![CBC sample](./sample%20reports/cbc-test.png) | ![CMP sample](./sample%20reports/cmp-test.png) | ![Thyroid sample](./sample%20reports/thyroid-profile-test.png) |

---

## Features

- **Comprehensive Report Support**
  - Supports 15+ common blood-test panel/layout variations (CBC, CMP, Lipid, LFT, KFT, Thyroid, Coagulation, Electrolytes, and more)
  - Accepts **PDF** and **image formats** (JPG, PNG) up to 10MB
  - Dual processing paths:
    - **OCR mode (primary):** GLM-OCR -> Gemini text extraction (secure-mode gated)
    - **Vision mode (fallback):** Gemini multimodal extraction (free-tier friendly)
  - Automatically groups tests into logical clinical categories

- **Smart Health Insights**
  - Left panel: animated biomarker cards grouped by category
  - Right panel: contextual interpretations that update on hover/click
  - Includes plain-language definitions, range comparisons, implications, and related markers

- **Health Score Overview**
  - Aggregates biomarkers into a single **Health Score** (0-100)
  - Shows normal, borderline, and abnormal counts with a radial gauge

- **Context-Aware AI Assistant**
  - Slide-up chat UI with full-screen mode
  - Receives full report context plus selected biomarker context
  - Answers test-specific questions in patient-friendly language

- **Modern UI / UX**
  - Responsive split-pane layout on desktop, stacked/mobile-optimized layout on phones
  - Motion-rich interactions built with Framer Motion

---

## Technical Highlights

- **Resilient dual pipeline:** `/api/analyze` dynamically switches between OCR-first and vision-first flows; OCR calls use retry logic with exponential backoff (`1s`, `2s`, `4s`) on transient failures.
- **Weighted health score algorithm:** `components/results-panel.tsx` computes `healthScore = ((total - abnormal*1.5 - borderline*0.5) / total) * 100`, then clamps to `0-100`.
- **Secure OCR access with abuse controls:** `/api/verify-ocr` uses timing-safe passphrase comparison, per-IP cooldown tracking, and a 60-second lockout after failed attempts.

---

## Tech Stack

- **Frontend**
  - [Next.js 16](https://nextjs.org/) (App Router)
  - [React 19](https://react.dev/)
  - [Tailwind CSS 4](https://tailwindcss.com/)
  - [Framer Motion](https://www.framer.com/motion/)
  - [Radix UI](https://www.radix-ui.com/) primitives
  - [lucide-react](https://lucide.dev/)
  - [react-markdown](https://github.com/remarkjs/react-markdown) + `remark-gfm`

- **Backend / AI**
  - Next.js API routes (`app/api/*`)
  - [@google/generative-ai](https://github.com/google-gemini/generative-ai-js) for extraction + chat
  - [GLM-OCR (Z.ai)](https://huggingface.co/zai-org/GLM-OCR) via `layout_parsing` API

- **Tooling & Deployment**
  - Node.js 22+
  - pnpm
  - [Vercel](https://vercel.com/)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/garg-tejas/blood-report-parser.git
cd blood-report-parser
```

### 2. Install dependencies

```bash
pnpm install
```

### 3. Configure environment variables

Copy the example file and add your keys:

```bash
cp .env.example .env
```

Edit `.env` with your values. The app works with only `GEMINI_API_KEY`; add `ZAI_API_KEY` and `OCR_PASSPHRASE` to enable secure OCR mode.

### 4. Start the development server

```bash
pnpm dev
```

Open `http://localhost:3000`.

---

## Project Structure

```text
.
|- app/
|  |- layout.tsx
|  |- page.tsx
|  |- api/
|  |  |- analyze/route.ts
|  |  |- chat/route.ts
|  |  `- verify-ocr/route.ts
|  `- globals.css
|- components/
|  |- upload-zone.tsx
|  |- results-panel.tsx
|  |- insights-panel.tsx
|  |- chat-drawer.tsx
|  |- ocr-unlock-dialog.tsx
|  `- ui/*
|- lib/
|  |- glm-ocr.ts
|  `- utils.ts
|- sample reports/
|- public/
`- README.md
```

---

## What I Learned

- OCR-first extraction is noticeably better on dense table-based reports, but fallback vision mode is essential for fast setup and cost control.
- Lightweight scoring heuristics work best when paired with transparent UI explanations (normal vs borderline vs abnormal) so users can trust the output.
- Paid model access needs first-class guardrails (timing-safe verification, cooldowns, and client lock states), not just hidden UI toggles.

---

## Future Improvements

- Add user accounts with persistent report history
- Track biomarker trends across multiple uploads
- Expand support for more specialized panels (hormones, tumor markers, genetics)
- Export annotated reports to PDF
- Add multilingual support for international report formats
