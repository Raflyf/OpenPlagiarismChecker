import re

with open('app/engine/web_scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add logging import
if 'import logging' not in content:
    content = content.replace('import os\n', 'import os\nimport logging\n\nlogger = logging.getLogger(__name__)\n', 1)

# Replace 'print(f"[!] ...' with 'logger.warning(...'
content = re.sub(r'print\(\s*f?"\[!?\]\s*([^"]+)"\s*\)', r'logger.warning("\1")', content)

# Replace print(f"... ")
content = re.sub(r'print\(\s*f"([^"]+)"\s*\)', r'logger.info("\1")', content)
content = re.sub(r'print\(\s*"([^"]+)"\s*\)', r'logger.info("\1")', content)

# Replace bare except Exception: pass
content = re.sub(r'except Exception:\s+pass', r'except Exception as e:\n        logger.debug("Silently caught exception: %s", e)', content)

# Also handle except Exception as e: pass
content = re.sub(r'except Exception as e:\s+pass', r'except Exception as e:\n        logger.debug("Silently caught exception: %s", e)', content)

with open('app/engine/web_scraper.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("web_scraper.py refactored successfully.")
