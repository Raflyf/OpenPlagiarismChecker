# OpenPlagiarismChecker

An open-source academic text similarity engine with modular architecture and reproducible evaluation. 

The project detects exact text overlap using n-gram matching and handles paraphrased text using multilingual semantic similarity (via Sentence Transformers). It is designed for reproducible local evaluation, transparent inspection, and extensible experimentation, with a special focus on Indonesian academic sources.

> **Disclaimer:** OpenPlagiarismChecker is an independent open-source project. It is not affiliated with, endorsed by, or intended to replace any commercial plagiarism detection service.

---

## What this project is
OpenPlagiarismChecker is a local, privacy-first document similarity checker. It processes PDF, DOCX, and TXT files, extracts the text, and cross-references it against millions of open-access academic papers, journals, and institutional repositories. By combining structural matching (n-gram shingling) and contextual matching (semantic similarity), it provides developers and researchers a transparent way to understand and analyze text overlap.

## Why it matters
Many plagiarism tools are closed, expensive, or opaque. This project provides a reproducible open-source alternative for students, developers, and researchers who want to inspect how similarity scoring works and improve it. The pipeline, search strategies, similarity algorithms, and evaluation methodologies are fully open for community review and contribution.

## Project status
This project is actively developed and used as a research and learning tool. The codebase is structured for iterative improvement, testing, and community contribution. 

## How Claude will help
Claude will be used to refactor code, improve documentation, review pull requests, help maintain cleaner architecture, and speed up development of open-source features and tests.

---

## Key Features
- **Exact Text Matching:** Uses 5-word n-gram shingling to detect direct text overlap.
- **Semantic Similarity:** Employs `paraphrase-multilingual-MiniLM-L12-v2` for paraphrased content detection.
- **File Support:** Processes PDF, DOCX, and TXT formats.
- **Local Web Interface:** Easy-to-use local dashboard for document upload and analysis.
- **Exportable Reports:** Generates structured HTML and PDF similarity reports.
- **Extensive Public Sources:** Queries 15+ academic APIs and public repositories (e.g., Indonesia OneSearch, Neliti, BASE, Semantic Scholar, OpenAlex, arXiv).
- **Modular Codebase:** Designed for experimentation and community contribution.

---

## How It Works

1. **Text Extraction:** Parses text from uploaded documents.
2. **Sampling:** Generates short phrase probes from the document.
3. **Source Discovery:** Queries public APIs and repositories using the probes.
4. **Text Retrieval:** Downloads open-access metadata or full text of the candidate sources.
5. **Layer 1 - Exact Match:** Applies n-gram shingling to find identical text segments.
6. **Layer 2 - Semantic Match:** Analyzes unmatched segments using a dynamic semantic threshold to find paraphrasing.
7. **Scoring:** Calculates the final ratio of matched words against the total document word count.

---

## Evaluation Benchmark

The system is evaluated against a core benchmark of recent academic documents to measure the gap between the engine's score and baseline reference tools.

**Core Benchmark (2026 dataset)**

| Document | Local Score | Reference Target | Delta (pp) |
| :--- | :---: | :---: | :---: |
| Laila after paraphrase | 3.45% | 4% | -0.55 |
| Hesti | 16.91% | 18% | -1.09 |
| Fikri | 13.95% | 14% | -0.05 |
| Rafly | 8.90% | 8% | +0.90 |
| Andyan | 22.26% | 23% | -0.74 |
| Dias Maulana | 21.20% | 23% | -1.80 |
| Melani | 18.74% | 19% | -0.26 |
| Laila before paraphrase | 22.09% | 24% | -1.91 |

*(Note: These results represent current benchmark performance and are continuously evaluated using Leave-One-Out Cross-Validation (LOOCV) to test threshold stability. They do not guarantee identical margins across all document types).*

---

## Installation

### 1-Click Setup
Clone or download this repository, then run the startup script for your OS:
- **Windows:** Double click `run.bat`
- **Linux / macOS:** Run `./run.sh`

The script automatically sets up the virtual environment, installs dependencies, and launches the web interface at `http://localhost:5001`.

### Manual Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Raflyf/OpenPlagiarismChecker.git
   cd OpenPlagiarismChecker
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   cd app
   python server.py
   ```

---

## Project Architecture

```text
OpenPlagiarismChecker/
├── app/
│   ├── server.py                 # Flask server 
│   ├── run_batch.py              # Batch execution runner
│   ├── run_test_groundtruth.py   # Validation runner
│   ├── calibrate_threshold.py    # Semantic threshold calibration
│   ├── test_documents/           # Benchmark documents
│   ├── frozen_corpus/            # Cached deterministic evaluation corpus
│   ├── corpus_bank/              # SQLite3 cache database
│   ├── engine/
│   │   ├── extractor.py          # Document parsing
│   │   ├── shingling.py          # N-Gram logic & thresholding
│   │   ├── semantic_similarity.py# Sentence-transformers pipeline
│   │   ├── web_scraper.py        # Concurrent web retrieval
│   │   ├── pdf_generator.py      # Report export
│   │   ├── priority_domains.py   # Academic repository mapping
│   │   ├── indonesian_repos.py   # Targeted repository scraper
│   │   └── free_api_fallbacks.py # API fallback handlers
│   ├── templates/                # Web interface HTML
│   └── static/                   # CSS and JS assets
└── requirements.txt
```

---

## Roadmap
- Expand the independent benchmark dataset across different languages and fields.
- Improve source discovery efficiency and reduce retrieval timeouts.
- Refine semantic similarity filtering to lower false-positive rates.
- Add comprehensive automated unit and integration tests.
- Improve developer documentation for individual engine components.

---

## Contribution
Contributions are highly welcomed. You can contribute by:
- Integrating new academic APIs or repositories.
- Adding verifiable benchmark datasets.
- Writing unit and integration tests.
- Optimizing CPU/GPU processing performance.
- Submitting bug fixes.

Please feel free to open an **Issue** or submit a **Pull Request**.

---

## License
OpenPlagiarismChecker is released under the **MIT License**.

This project is intended for open-source research, education, experimentation, and independent similarity analysis.
