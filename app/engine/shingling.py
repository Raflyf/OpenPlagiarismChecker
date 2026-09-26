import re
import math
import os
import logging
from functools import lru_cache
from .semantic_similarity import batch_semantic_check

logger = logging.getLogger(__name__)

# Pre-compiled Regex Patterns (Phase 3 #7)
RE_NEWLINE = re.compile(r'\n+')
RE_SENTENCE_SPLIT = re.compile(r'(?<=[.!?;])\s+')
RE_RAW_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')
RE_HYPHENATION = re.compile(r'-\s+')
RE_NON_ALPHANUMERIC = re.compile(r'[^\w\s]')

# Magic Numbers extracted to constants (Phase 3 #6)
SEMANTIC_THRESH_BASE = 0.7900  # Titik Sweetspot (Base optimum)
SEMANTIC_THRESH_MULTIPLIER = 0.0250 # Pengali N-Gram Synergy
DEFAULT_CHUNK_MAX_WORDS = 40
NGRAM_SIZE = 5

COMMON_ACADEMIC_PHRASES = {
    "yang telah dilakukan oleh", "dalam penelitian ini penulis", "berdasarkan hasil penelitian yang",
    "dari hasil penelitian ini", "dapat disimpulkan bahwa hasil", "metode yang digunakan dalam",
    "data yang diperoleh dari", "hasil penelitian menunjukkan bahwa", "penelitian ini bertujuan untuk",
    "teknik pengumpulan data yang", "populasi dan sampel dalam", "analisis data menggunakan metode",
    "hasil dan pembahasan dalam", "berdasarkan latar belakang masalah", "rumusan masalah dalam penelitian",
    "manfaat penelitian ini adalah", "batasan masalah dalam penelitian", "definisi operasional variabel dalam",
    "kerangka berpikir dalam penelitian", "hipotesis penelitian ini adalah", "jenis penelitian yang digunakan",
    "sumber data dalam penelitian", "teknik analisis data yang", "uji validitas dan reliabilitas",
    "hasil uji hipotesis menunjukkan", "ini penulis menggunakan metode", "penulis menggunakan metode yang",
    "menggunakan metode yang telah", "penelitian ini menggunakan metode", "yang digunakan dalam penelitian",
    "digunakan dalam penelitian ini", "ini adalah penelitian yang", "sampel dalam penelitian ini",
    "penelitian ini adalah untuk", "tujuan penelitian ini adalah", "objek penelitian ini adalah",
    "subjek penelitian ini adalah", "lokasi penelitian ini adalah", "waktu penelitian ini dilakukan",
    "variabel dalam penelitian ini", "instrumen dalam penelitian ini", "indikator dalam penelitian ini",
    "penelitian ini dilakukan di", "penelitian ini dilakukan pada", "penelitian ini dilakukan untuk",
    "metode penelitian yang digunakan", "pendekatan yang digunakan dalam", "teknik yang digunakan dalam",
    "analisis yang digunakan dalam", "berdasarkan hasil analisis yang", "berdasarkan hasil observasi yang",
    "berdasarkan data yang diperoleh", "berdasarkan tabel di atas", "berdasarkan gambar di atas",
    "berdasarkan grafik di atas", "dari tabel di atas", "dari gambar di atas", "pada tabel di atas",
    "pada gambar di atas", "seperti yang terlihat pada", "seperti yang ditunjukkan pada",
    "hal ini menunjukkan bahwa", "hal ini disebabkan oleh", "hal ini dikarenakan oleh",
    "hal ini sesuai dengan", "hal ini sejalan dengan", "hal ini berbeda dengan",
    "dengan demikian dapat disimpulkan", "oleh karena itu dapat", "oleh karena itu penelitian",
    "oleh karena itu penulis", "dengan kata lain bahwa", "adapun yang menjadi tujuan",
    "adapun yang menjadi manfaat", "adapun yang menjadi rumusan"
}

def is_common_phrase(ngram_text):
    if ngram_text in COMMON_ACADEMIC_PHRASES:
        return True
    return any(phrase in ngram_text for phrase in COMMON_ACADEMIC_PHRASES)

def get_sentences(text: str, filter_short: bool = False) -> list[str]:
    text = RE_NEWLINE.sub('. ', text)
    sentences = RE_SENTENCE_SPLIT.split(text)
    if filter_short:
        return [s.strip() for s in sentences if len(s.split()) >= 3]
    return [s.strip() for s in sentences if s.strip()]

def build_sentence_word_spans(doc_text: str, max_words: int = DEFAULT_CHUNK_MAX_WORDS) -> list[tuple[str, int, int]]:
    spans = []
    current_word_idx = 0
    for raw_sent in RE_RAW_SENTENCE_SPLIT.split(doc_text):
        if not (raw_sent := raw_sent.strip()): continue
        words = raw_sent.split()
        for i in range(0, len(words), max_words):
            chunk = words[i:i+max_words]
            chunk_len = len(chunk)
            spans.append((' '.join(chunk), current_word_idx, current_word_idx + chunk_len))
            current_word_idx += chunk_len
    return spans

@lru_cache(maxsize=20000)
def get_ngrams_cached(text: str, n: int = NGRAM_SIZE) -> list[str]:
    words = RE_NON_ALPHANUMERIC.sub('', RE_HYPHENATION.sub('', text)).lower().split()
    return [g for i in range(len(words)-n+1) if not is_common_phrase(g := " ".join(words[i:i+n]))]

def get_ngrams(text: str, n: int = NGRAM_SIZE) -> list[str]:
    return get_ngrams_cached(text, n)

def get_shingles(text: str, n: int = NGRAM_SIZE) -> set[str]:
    return set(get_ngrams_cached(text, n))


class SimilarityCalculator:
    """Builder pattern class for calculating plagiarism similarity. (Phase 4 #3)"""
    def __init__(self, doc_text, corpus, current_filename: str = "", current_hash: str = ""):
        self.doc_text = RE_HYPHENATION.sub('', doc_text)
        self.corpus = corpus
        # [FITUR SELF-EXCLUSION 26 Sep] Identitas dokumen saat ini — dipakai untuk
        # mengecualikan kecocokan dengan submission lama milik dokumen yang sama
        # (mis. mahasiswa submit bab per bab atau versi revisi).
        self.current_filename = current_filename
        self.current_hash = current_hash
        self.excluded_self_sources = []
        self.exclude_small = False
        self.use_semantic = False
        self.semantic_threshold = "auto"
        self.semantic_max_sources = None
        # [AUDIT FIX 26 Sep] KONSISTENSI METODOLOGI: nilai ini WAJIB sama dengan
        # default calculate_similarity() yang dipakai run_test_groundtruth.py (=1).
        # Versi lama = 3 sementara groundtruth = 1 -> skor server TIDAK identik dengan
        # skor validasi yang diklaim di README/docs (klaim "metodologi identik" tidak benar).
        # Nilai 1 = abaikan hanya sumber tanpa overlap sama sekali; filter sumber kecil
        # tetap dilakukan lewat exclude_small (tampilan >=1%) tanpa mengubah skor total.
        self.min_source_overlap = 1
        self.is_cancelled_cb = None

        self.doc_spans = []
        self.doc_words = []
        self.total_doc_words = 0
        self.clean_doc_words = []
        self.total_doc_ngrams = set()
        # [FITUR 26 Sep] Hasil per-section diisi saat calculate() selesai.
        self.section_scores = []

    def set_exclude_small(self, exclude_small):
        self.exclude_small = exclude_small
        return self

    def set_semantic(self, use_semantic, threshold="auto", max_sources=None):
        self.use_semantic = use_semantic
        self.semantic_threshold = threshold
        self.semantic_max_sources = max_sources
        return self

    def set_min_source_overlap(self, min_overlap):
        self.min_source_overlap = min_overlap
        return self

    def set_cancel_callback(self, cb):
        self.is_cancelled_cb = cb
        return self

    def _initialize_document(self):
        self.doc_spans = build_sentence_word_spans(self.doc_text)
        self.doc_words = self.doc_text.split()
        self.total_doc_words = len(self.doc_words)
        
        if self.total_doc_words > 0:
            self.total_doc_ngrams = set(get_ngrams(self.doc_text, n=NGRAM_SIZE))
            self.clean_doc_words = [RE_NON_ALPHANUMERIC.sub('', w).lower() for w in self.doc_words]

    def _check_cancelled(self):
        if self.is_cancelled_cb and self.is_cancelled_cb():
            logger.info("PROSES DIBATALKAN USER: Menghentikan kalkulasi.")
            return True
        return False

    def _fill_gaps(self, match_array: list[bool]):
        """Gap Filling konservatif: butuh >= 2 kata match di KEDUA sisi gap"""
        n = len(match_array)
        for i in range(n - 4):
            if match_array[i] and i > 0 and match_array[i-1] and not match_array[i+1]:
                for gap in (2, 3):
                    if i + gap + 1 < n and match_array[i+gap] and match_array[i+gap+1]:
                        match_array[i+1:i+gap] = [True] * (gap - 1)
                        break

    def calculate(self):
        self._initialize_document()
        if not self.doc_spans or self.total_doc_words == 0 or not self.corpus:
            return [], 0.0, []

        # [FITUR SELF-EXCLUSION 26 Sep] Buang sumber yang merupakan submission lama
        # dari dokumen yang SAMA (versi revisi / bab terpisah). Tanpa ini, dokumen
        # yang di-submit ulang akan "memiripkan dirinya sendiri" -> skor palsu tinggi.
        if self.current_filename or self.current_hash:
            try:
                from .quote_intelligence import is_self_match
            except ImportError:
                try:
                    from quote_intelligence import is_self_match
                except ImportError:
                    is_self_match = None
            if is_self_match is not None:
                filtered = {}
                for url, text in self.corpus.items():
                    if is_self_match(url, self.current_filename, self.current_hash):
                        self.excluded_self_sources.append(url)
                    else:
                        filtered[url] = text
                if self.excluded_self_sources:
                    logger.info("Self-exclusion: %d sumber (submission lama dokumen yang sama) dikecualikan.",
                                len(self.excluded_self_sources))
                    self.corpus = filtered

        sources_report = {}
        
        # 1. N-Gram Matching
        for url, source_text in self.corpus.items():
            s_ngrams = set(get_ngrams(source_text, n=NGRAM_SIZE))
            overlap_ngrams = self.total_doc_ngrams.intersection(s_ngrams)
            
            if not overlap_ngrams or len(overlap_ngrams) < self.min_source_overlap:
                continue
                
            is_matched_source = [False] * len(self.doc_words)
            for i in range(len(self.doc_words) - NGRAM_SIZE + 1):
                ngram = " ".join(self.clean_doc_words[i:i+NGRAM_SIZE])
                if ngram in overlap_ngrams:
                    for j in range(NGRAM_SIZE):
                        is_matched_source[i+j] = True
                        
            self._fill_gaps(is_matched_source)
                        
            matched_word_count = sum(is_matched_source)
            percentage = (matched_word_count / self.total_doc_words) * 100.0

            if percentage > 0:
                sources_report[url] = {
                    'percentage': float(percentage),
                    'matched_words': int(matched_word_count),
                    'url': url,
                    'sort_score': float(percentage),
                    'overlap_ngrams': overlap_ngrams
                }

        sorted_sources = sorted(list(sources_report.values()), key=lambda x: x['sort_score'], reverse=True)
        top_sources = sorted_sources[:20]

        # 2. Global Aggregation
        global_overlap_ngrams = set()
        for s in sorted_sources:
            global_overlap_ngrams.update(s['overlap_ngrams'])
            
        is_matched_global = [False] * len(self.doc_words)
        for i in range(len(self.doc_words) - NGRAM_SIZE + 1):
            ngram = " ".join(self.clean_doc_words[i:i+NGRAM_SIZE])
            if ngram in global_overlap_ngrams:
                for j in range(i, i+NGRAM_SIZE):
                    is_matched_global[j] = True

        self._fill_gaps(is_matched_global)

        plagiarized_sentences_data = []
        current_phrase = []
        for i in range(len(self.doc_words)):
            if is_matched_global[i]:
                current_phrase.append(self.doc_words[i])
            else:
                if len(current_phrase) >= NGRAM_SIZE:
                    phrase_text = " ".join(current_phrase)
                    p_ngrams = set(get_ngrams(phrase_text, n=NGRAM_SIZE))
                    best_source_id = 1
                    best_overlap = 0
                    for idx, source in enumerate(top_sources):
                        olap = len(p_ngrams.intersection(source['overlap_ngrams']))
                        if olap > best_overlap:
                            best_overlap = olap
                            best_source_id = idx + 1
                            
                    plagiarized_sentences_data.append({
                        'text': phrase_text,
                        'source_id': best_source_id
                    })
                current_phrase = []
                
        if len(current_phrase) >= NGRAM_SIZE:
            phrase_text = " ".join(current_phrase)
            p_ngrams = set(get_ngrams(phrase_text, n=NGRAM_SIZE))
            best_source_id = 1
            best_overlap = 0
            for idx, source in enumerate(top_sources):
                olap = len(p_ngrams.intersection(source.get('overlap_ngrams', set())))
                if olap > best_overlap:
                    best_overlap = olap
                    best_source_id = idx + 1
            plagiarized_sentences_data.append({
                'text': phrase_text,
                'source_id': best_source_id
            })

        for s in sorted_sources:
            s.pop('overlap_ngrams', None)

        total_plagiarized_words_global = sum(is_matched_global)
        ngram_similarity = float((total_plagiarized_words_global / self.total_doc_words) * 100.0)
        
        # 3. Semantic Similarity
        if self._check_cancelled():
            return [], 0.0, []

        semantic_plagiarized_words = 0
        if self.use_semantic and self.corpus:
            if self.semantic_threshold == "auto":
                thresh_val = SEMANTIC_THRESH_BASE + SEMANTIC_THRESH_MULTIPLIER * math.sqrt(ngram_similarity)
                self.semantic_threshold = round(thresh_val, 4)
            
            logger.info("===== STARTING SEMANTIC SIMILARITY CHECK =====")
            logger.info("Threshold: %s, Total sentences: %s", self.semantic_threshold, len(self.doc_spans))
            
            unmatched_sentences = []
            unmatched_indices = []
            sentence_word_positions = []
            
            for sent_idx, (sentence, sent_start, sent_end) in enumerate(self.doc_spans):
                if sent_end > len(is_matched_global):
                    sent_end = len(is_matched_global)
                sent_word_count = sent_end - sent_start
                matched_in_sentence = sum(is_matched_global[sent_start:sent_end])
                match_ratio = matched_in_sentence / sent_word_count if sent_word_count > 0 else 0
                
                sentence_word_positions.append((sent_start, sent_end))
                if match_ratio < 0.35 and sent_word_count >= 5:
                    unmatched_sentences.append(sentence)
                    unmatched_indices.append(sent_idx)
            
            logger.info("Found %s unmatched sentences for semantic check", len(unmatched_sentences))
            
            if unmatched_sentences:
                ngram_urls = [s['url'] for s in sorted_sources if s.get('percentage', 0) > 0.0]
                ngram_set = set(ngram_urls)
                non_overlap_urls = [u for u in self.corpus.keys() if u not in ngram_set][:100]
                candidate_urls = ngram_urls + non_overlap_urls
                if self.semantic_max_sources is not None:
                    candidate_urls = candidate_urls[:self.semantic_max_sources]
                    
                semantic_corpus = {u: self.corpus[u] for u in candidate_urls if u in self.corpus}
                corpus_by_sentence = {url: get_sentences(text, filter_short=True) for url, text in semantic_corpus.items()}
                
                semantic_results = batch_semantic_check(
                    unmatched_sentences, 
                    corpus_by_sentence, 
                    threshold=self.semantic_threshold
                )
                
                logger.info("Semantic check found %s potential paraphrase matches", len(semantic_results))
                
                semantic_matches_temp = []
                for unmatched_idx, matches in semantic_results.items():
                    if matches:
                        actual_sent_idx = unmatched_indices[unmatched_idx]
                        best_match = matches[0]
                        
                        plagiarized_sentences_data.append({
                            'text': unmatched_sentences[unmatched_idx],
                            'source_id': len(top_sources) + 1,
                            'detection_method': 'semantic',
                            'similarity_score': best_match['similarity_score'],
                            'matched_source': best_match['source_url'],
                            'matched_text': best_match['matched_text']
                        })
                        
                        source_url = best_match['source_url']
                        sent_start, sent_end = sentence_word_positions[actual_sent_idx]
                        newly_detected_words = 0
                        for word_idx in range(sent_start, sent_end):
                            if word_idx < len(is_matched_global) and not is_matched_global[word_idx]:
                                newly_detected_words += 1
                                    
                        semantic_matches_temp.append({
                            'sent_start': sent_start,
                            'sent_end': sent_end,
                            'source_url': source_url,
                            'newly_detected_words': newly_detected_words
                        })
                        
                        if source_url not in sources_report:
                            sources_report[source_url] = {
                                'percentage': 0.0,
                                'matched_words': 0,
                                'url': source_url,
                                'sort_score': 0.0,
                                'detection_method': 'semantic'
                            }
                        
                        sources_report[source_url]['matched_words'] += newly_detected_words
                        sources_report[source_url]['percentage'] = (sources_report[source_url]['matched_words'] / self.total_doc_words) * 100.0
                        sources_report[source_url]['sort_score'] = sources_report[source_url]['percentage']
                
                for match_data in semantic_matches_temp:
                    semantic_plagiarized_words += match_data['newly_detected_words']
                    for word_idx in range(match_data['sent_start'], match_data['sent_end']):
                        if word_idx < len(is_matched_global):
                            is_matched_global[word_idx] = True

                sorted_sources = sorted(list(sources_report.values()), key=lambda x: x['sort_score'], reverse=True)
                top_sources = sorted_sources[:20]
        
        semantic_additional_pct = (semantic_plagiarized_words / self.total_doc_words * 100.0) if self.total_doc_words else 0.0
        raw_combined_similarity = float((sum(is_matched_global) / self.total_doc_words) * 100.0)
        total_similarity = raw_combined_similarity

        # --- Kalibrasi Terdokumentasi (Anti-Manipulasi) ---
        # [AUDIT FIX 26 Sep] Versi lama mengurangi skor secara FLAT -1.2% ke semua
        # dokumen hanya agar angka "cocok" dengan sistem referensi. Itu adalah
        # manipulasi skor, bukan kalibrasi — dan membuat skor tidak dapat
        # dipertanggungjawabkan secara akademik.
        #
        # Kalibrasi yang SAH adalah yang diterapkan pada PARAMETER (threshold semantic),
        # bukan pada hasil akhir. Kalibrasi threshold sudah dihitung secara empiris:
        #   threshold = SEMANTIC_THRESH_BASE + SEMANTIC_THRESH_MULTIPLIER * sqrt(ngram)
        # dengan konstanta yang di-sweep terhadap benchmark (lihat calibration_result.json).
        # Skor akhir = murni hasil perhitungan overlap N-Gram + Semantic, tanpa potongan.
        #
        # Backward-compat: bila ada yang butuh mode kalibrasi lama (mis. untuk analisis),
        # bisa diaktifkan via env SCORE_CALIBRATION_OFFSET (default 0 = TANPA potongan).
        calibration_offset = float(os.environ.get("SCORE_CALIBRATION_OFFSET", "0"))
        calibration_ratio = 1.0
        if calibration_offset != 0 and total_similarity > 0:
            calibrated_total = max(0.0, total_similarity - calibration_offset)
            calibration_ratio = calibrated_total / total_similarity
            total_similarity = calibrated_total

            for source in sorted_sources:
                source['percentage'] *= calibration_ratio
                source['sort_score'] = source['percentage']

        display_sources = sorted_sources
        if self.exclude_small:
            display_sources = [s for s in sorted_sources if s['percentage'] >= 1.0]
            if not display_sources and total_similarity >= 1.0:
                display_sources = sorted_sources[:10]

        # [FITUR 26 Sep] Per-Section Breakdown: skor per bab/section.
        # Dihitung dari array match global yang sudah final (termasuk semantic).
        section_scores = []
        try:
            section_scores = compute_section_scores(self.doc_text, is_matched_global, self.doc_words)
        except Exception as sec_e:
            logger.debug("Per-section scoring gagal: %s", sec_e)

        # [FITUR 26 Sep] Character n-gram fuzzy: tandai sumber yang punya banyak
        # fragmen karakter identik (indikasi penyalinan dengan modifikasi huruf).
        # TIDAK menambah skor — hanya anotasi transparansi per sumber.
        try:
            for source in sorted_sources:
                src_url = source.get('url', '')
                src_text = self.corpus.get(src_url, '')
                if src_text:
                    fuzzy = compute_char_fuzzy_overlap(self.doc_text, src_text)
                    if fuzzy >= CHAR_FUZZY_MIN_OVERLAP:
                        source['char_fuzzy_overlap'] = round(fuzzy, 3)
        except Exception as fz_e:
            logger.debug("Char fuzzy overlap gagal: %s", fz_e)

        self.section_scores = section_scores
        self.ngram_similarity = ngram_similarity
        self.semantic_similarity = semantic_additional_pct
        self.raw_similarity = raw_combined_similarity
        self.calibrated_similarity = total_similarity

        logger.info("===== DETECTION SUMMARY =====")
        logger.info("Layer 1 (N-Gram Exact Match)       : %.2f%%", ngram_similarity)
        logger.info("Layer 2 (Semantic Paraphrase Extra): +%.2f%%", semantic_additional_pct)
        logger.info("Total Raw Similarity (Layer 1 + 2) : %.2f%%", raw_combined_similarity)
        logger.info("Final Calibrated Similarity (-1.2%): %.2f%%", total_similarity)
        logger.info("Sumber ditampilkan (>=1%%)          : %d dari %d sumber ber-overlap", len(display_sources), len(sorted_sources))

        return display_sources, total_similarity, plagiarized_sentences_data

# ============================================================================
# [FITUR 26 Sep] Per-Section Breakdown — skor per bab/section seperti Turnitin
# ============================================================================

# Pola heading bab/section akademik Indonesia & Inggris
# Pola heading bab/section akademik.
# [FIX 26 Sep] Versi pertama hanya menemukan 1 section dari 3 karena alternasi
# romawi "I{1,3}V?|IV|V|VI{0,3}|IX|X" TIDAK mencakup "II" dan "III" (regex engine
# mencoba "I" dulu lalu gagal pada "I I", dan `\b` setelah "I" tidak cocok karena
# diikuti huruf I lagi). Sekarang romawi ditulis lengkap dan diurutkan terpanjang
# dulu (III sebelum II sebelum I) agar tidak terpotong.
_RE_SECTION_HEADINGS = re.compile(
    r"(?:^|\n)[ \t]*("
    r"BAB\s+(?:XX|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I|\d{1,2})\b[^\n]{0,80}"
    r"|(?:CHAPTER|SECTION)\s+\d+\b[^\n]{0,80}"
    r"|\d+\.\s*[A-Z][^\n]{3,60}"
    r"|(?:PENDAHULUAN|TINJAUAN PUSTAKA|LANDASAN TEORI|METODOLOGI PENELITIAN|METODE PENELITIAN|HASIL DAN PEMBAHASAN|PEMBAHASAN|KESIMPULAN(?: DAN SARAN)?|ABSTRACT|ABSTRAK)\s*(?:\n|$)"
    r")",
    re.M | re.I,
)


def detect_sections(doc_text: str) -> list:
    """Deteksi section/bab dalam dokumen.

    Mengembalikan list of (label, start_char, end_char). Bila tidak ada heading
    yang terdeteksi, kembalikan satu section "Seluruh Dokumen".
    """
    if not doc_text:
        return []

    matches = list(_RE_SECTION_HEADINGS.finditer(doc_text))
    if not matches:
        return [("Seluruh Dokumen", 0, len(doc_text))]

    sections = []
    for i, m in enumerate(matches):
        label = re.sub(r"\s+", " ", m.group(1)).strip()[:70]
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(doc_text)
        if end - start < 100:  # section terlalu pendek = kemungkinan false heading
            continue
        sections.append((label, start, end))

    if not sections:
        return [("Seluruh Dokumen", 0, len(doc_text))]
    return sections


def compute_section_scores(doc_text: str, is_matched_global: list, doc_words: list) -> list:
    """Hitung skor kemiripan per section berdasarkan word-level match array.

    Menghubungkan posisi karakter section ke indeks kata: setiap section dihitung
    persentase kata yang match di dalam rentang katanya sendiri.
    """
    if not doc_text or not doc_words or not is_matched_global:
        return []

    sections = detect_sections(doc_text)
    if not sections:
        return []

    # Bangun peta karakter -> indeks kata (berbasis prefix count spasi).
    # Sederhana & O(n): hitung jumlah kata sebelum posisi karakter tertentu.
    word_starts = []
    pos = 0
    for w in doc_words:
        idx = doc_text.find(w, pos)
        if idx < 0:
            idx = pos
        word_starts.append(idx)
        pos = idx + len(w)

    results = []
    for label, c_start, c_end in sections:
        # Cari indeks kata pertama & terakhir dalam rentang karakter section
        first = 0
        for i, ws in enumerate(word_starts):
            if ws >= c_start:
                first = i
                break
        last = len(word_starts) - 1
        for i in range(len(word_starts) - 1, -1, -1):
            if word_starts[i] < c_end:
                last = i
                break

        if last < first:
            continue
        total = last - first + 1
        if total < 20:  # section sangat pendek tidak bermakna
            continue
        matched = sum(1 for i in range(first, min(last + 1, len(is_matched_global))) if is_matched_global[i])
        pct = (matched / total) * 100.0 if total else 0.0
        results.append({
            "label": label,
            "percentage": round(pct, 2),
            "matched_words": int(matched),
            "total_words": int(total),
        })

    return results


# ============================================================================
# [FITUR 26 Sep] Character N-Gram (Fuzzy) — deteksi plagiat dengan modifikasi
# huruf. Word-level 5-gram bisa lolos bila 1-2 huruf diganti per kata
# (mis. "penelitian" -> "penelitlan"). Character 4-gram menangkap ini.
# ============================================================================

CHAR_NGRAM_SIZE = 4
# Ambang: overlap char-ngram minimal agar dianggap kecocokan fuzzy (bukan kebetulan)
CHAR_FUZZY_MIN_OVERLAP = float(os.environ.get("CHAR_FUZZY_MIN_OVERLAP", "0.35"))


def get_char_ngrams(text: str, n: int = CHAR_NGRAM_SIZE) -> set:
    """Character n-gram dari teks yang dinormalisasi (tanpa spasi/tanda baca)."""
    clean = re.sub(r"[^a-z0-9]", "", text.lower())
    if len(clean) < n:
        return set()
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def compute_char_fuzzy_overlap(doc_text: str, source_text: str) -> float:
    """Rasio overlap character n-gram antara dokumen & satu sumber.

    Mengembalikan 0.0-1.0. Nilai tinggi = ada banyak fragmen karakter identik
    yang menandakan penyalinan dengan modifikasi kecil.
    """
    if not doc_text or not source_text:
        return 0.0
    doc_grams = get_char_ngrams(doc_text)
    if not doc_grams:
        return 0.0
    src_grams = get_char_ngrams(source_text)
    if not src_grams:
        return 0.0
    overlap = len(doc_grams & src_grams)
    return overlap / len(doc_grams)


def calculate_similarity(doc_text, corpus, exclude_small=False, use_semantic=False, semantic_threshold="auto", semantic_max_sources=None, min_source_overlap=1, is_cancelled_cb=None):
    """
    Backwards compatibility function that uses the SimilarityCalculator.
    """
    calculator = SimilarityCalculator(doc_text, corpus)
    calculator.set_exclude_small(exclude_small)
    calculator.set_semantic(use_semantic, semantic_threshold, semantic_max_sources)
    calculator.set_min_source_overlap(min_source_overlap)
    calculator.set_cancel_callback(is_cancelled_cb)
    
    return calculator.calculate()
