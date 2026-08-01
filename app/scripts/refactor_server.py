import re

with open('app/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add logging
if 'import logging as _logging' in content:
    content = content.replace("import logging as _logging\n_logging.getLogger('werkzeug').setLevel(_logging.WARNING)", 
                              "import logging\nlogging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')\nlogger = logging.getLogger(__name__)\nlogging.getLogger('werkzeug').setLevel(logging.WARNING)", 1)

# Metrics variables
if 'PROMETHEUS METRICS' not in content:
    metrics_code = """
# PROMETHEUS METRICS
import time as time_mod
_metric_total_docs = 0
_metric_total_errors = 0
_metric_processing_time = 0.0

@app.route('/metrics')
def metrics():
    # Phase 4 #4: Tambahkan monitoring dan observability stack
    lines = [
        "# HELP plagiarism_total_documents Total dokumen diproses",
        "# TYPE plagiarism_total_documents counter",
        f"plagiarism_total_documents {_metric_total_docs}",
        "# HELP plagiarism_total_errors Total error saat pemrosesan",
        "# TYPE plagiarism_total_errors counter",
        f"plagiarism_total_errors {_metric_total_errors}",
        "# HELP plagiarism_processing_time_seconds Total durasi waktu proses (detik)",
        "# TYPE plagiarism_processing_time_seconds counter",
        f"plagiarism_processing_time_seconds {_metric_processing_time}"
    ]
    from flask import Response
    return Response("\\n".join(lines), mimetype="text/plain")
"""
    content = content.replace("app = Flask(__name__)", "app = Flask(__name__)\n" + metrics_code, 1)

# Replace prints with logger
content = re.sub(r'print\(\s*f?"\[!\]\s*([^"]+)"\s*\)', r'logger.info(f"\1")', content)
content = re.sub(r'print\(\s*"\[!\]\s*([^"]+)"\s*\)', r'logger.info("\1")', content)

# Fix specific variables inside logger that need formatting
content = content.replace('logger.info(f"Cleanup: {cleaned_count} file temporary', 'logger.info(f"Cleanup: {cleaned_count} file temporary')
content = content.replace('logger.info(f"PROSES DIBATALKAN USER: {file_id}")', 'logger.info(f"PROSES DIBATALKAN USER: {file_id}")')

# Rate limiting fix
old_rate_limit = """def _check_rate_limit(ip):
    \"\"\"Check rate limit for IP. Returns (allowed, remaining_time)\"\"\"
    now = time.time()
    with _rate_limit_lock:
        if ip not in _rate_limit_db:
            _rate_limit_db[ip] = []
        # Remove old entries
        _rate_limit_db[ip] = [t for t in _rate_limit_db[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_limit_db[ip]) >= RATE_LIMIT_MAX_REQUESTS:
            oldest = _rate_limit_db[ip][0]
            remaining = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
            return False, remaining
        _rate_limit_db[ip].append(now)
        return True, 0"""

new_rate_limit = """def get_client_ip():
    \"\"\"Phase 4 #2: Rate limiting dengan proper IP extraction\"\"\"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def _check_rate_limit(ip):
    \"\"\"Check rate limit for IP. Returns (allowed, remaining_time)\"\"\"
    now = time.time()
    with _rate_limit_lock:
        if ip not in _rate_limit_db:
            _rate_limit_db[ip] = []
        _rate_limit_db[ip] = [t for t in _rate_limit_db[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_limit_db[ip]) >= RATE_LIMIT_MAX_REQUESTS:
            oldest = _rate_limit_db[ip][0]
            remaining = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
            return False, remaining
        _rate_limit_db[ip].append(now)
        return True, 0"""

content = content.replace(old_rate_limit, new_rate_limit)
content = content.replace("client_ip = request.remote_addr or 'unknown'", "client_ip = get_client_ip()")

# Add metric tracking in process_document
track_start = "start_time_process = time.time()"
if track_start not in content:
    content = content.replace("def process_document(", "def process_document(")
    content = content.replace("def check_cancelled():", f"global _metric_total_docs, _metric_total_errors, _metric_processing_time\n        start_time_process = time.time()\n        def check_cancelled():")

# Successful complete
track_end = "_metric_total_docs += 1\n        _metric_processing_time += (time.time() - start_time_process)"
if track_end not in content:
    content = content.replace("print(f\"Selesai. Hasil: {total_similarity}%\")", f"logger.info(f\"Selesai. Hasil: {{total_similarity}}%\")\n        _metric_total_docs += 1\n        _metric_processing_time += (time.time() - start_time_process)")

# Error track
track_err = "_metric_total_errors += 1"
if track_err not in content:
    content = content.replace("traceback.print_exc()", f"traceback.print_exc()\n        global _metric_total_errors\n        _metric_total_errors += 1")

with open('app/server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("server.py refactored successfully.")
