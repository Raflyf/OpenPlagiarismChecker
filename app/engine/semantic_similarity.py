"""
Semantic Similarity Module for Paraphrase Detection
Uses sentence-transformers to detect paraphrased content that N-Gram might miss
"""

from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np

# Global model instance (loaded once for efficiency)
_model = None

def get_model(force_cpu=False):
    """
    Load and cache the sentence-transformers model.
    Using 'paraphrase-multilingual-MiniLM-L12-v2' - a lightweight but effective model for semantic similarity in Indonesian.
    """
    global _model
    if force_cpu or _model is None:
        device = "cpu" if force_cpu else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[!] Loading Sentence-Transformer model for semantic similarity... (device={device})")
        _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
        print(f"[!] Model loaded successfully on {device.upper()}.")
    return _model

def calculate_semantic_similarity(sentence1, sentence2):
    """
    Calculate semantic similarity between two sentences.
    """
    model = get_model()
    try:
        embedding1 = model.encode(sentence1, convert_to_tensor=True)
        embedding2 = model.encode(sentence2, convert_to_tensor=True)
    except Exception as e:
        if "cuda" in str(e).lower():
            print(f"[!] CUDA Error ({e}). Fallback ke CPU...")
            model = get_model(force_cpu=True)
            embedding1 = model.encode(sentence1, convert_to_tensor=True)
            embedding2 = model.encode(sentence2, convert_to_tensor=True)
        else:
            raise e
    
    similarity = util.pytorch_cos_sim(embedding1, embedding2).item()
    return similarity

def find_semantic_matches(query_sentences, corpus_sentences, threshold=0.88):
    model = get_model()
    print(f"[!] Generating embeddings for {len(query_sentences)} query sentences...")
    try:
        query_embeddings = model.encode(query_sentences, convert_to_tensor=True, show_progress_bar=True)
    except Exception as e:
        if "cuda" in str(e).lower():
            print(f"[!] CUDA Error ({e}). Fallback ke CPU...")
            model = get_model(force_cpu=True)
            query_embeddings = model.encode(query_sentences, convert_to_tensor=True, show_progress_bar=True)
        else:
            raise e
    
    semantic_matches = {}
    for source_url, source_sentences in corpus_sentences.items():
        if not source_sentences:
            continue
            
        print(f"[!] Checking semantic similarity with {source_url}...")
        try:
            source_embeddings = model.encode(source_sentences, convert_to_tensor=True, show_progress_bar=False)
        except Exception as e:
            if "cuda" in str(e).lower():
                print(f"[!] CUDA Error ({e}). Fallback ke CPU...")
                model = get_model(force_cpu=True)
                query_embeddings = model.encode(query_sentences, convert_to_tensor=True, show_progress_bar=False)
                source_embeddings = model.encode(source_sentences, convert_to_tensor=True, show_progress_bar=False)
            else:
                raise e
        
        similarity_matrix = util.pytorch_cos_sim(query_embeddings, source_embeddings)
        for query_idx in range(len(query_sentences)):
            for source_idx in range(len(source_sentences)):
                similarity_score = similarity_matrix[query_idx][source_idx].item()
                if similarity_score >= threshold:
                    if query_idx not in semantic_matches:
                        semantic_matches[query_idx] = []
                    semantic_matches[query_idx].append({
                        'source_url': source_url,
                        'matched_text': source_sentences[source_idx],
                        'similarity_score': similarity_score,
                        'detection_method': 'semantic'
                    })
    
    for query_idx in semantic_matches:
        semantic_matches[query_idx].sort(key=lambda x: x['similarity_score'], reverse=True)
    return semantic_matches

def batch_semantic_check(unmatched_sentences, corpus_sentences, threshold=0.88, batch_size=32):
    if not unmatched_sentences:
        return {}
    
    model = get_model()
    print(f"[!] Performing semantic similarity check on {len(unmatched_sentences)} unmatched sentences...")
    
    try:
        query_embeddings = model.encode(unmatched_sentences, convert_to_tensor=True, 
                                       batch_size=batch_size, show_progress_bar=True)
    except Exception as e:
        if "cuda" in str(e).lower():
            print(f"[!] CUDA Error ({e}). Fallback otomatis ke CPU...")
            model = get_model(force_cpu=True)
            query_embeddings = model.encode(unmatched_sentences, convert_to_tensor=True, 
                                           batch_size=batch_size, show_progress_bar=True)
        else:
            raise e
    
    # === OPTIMASI: Gabungkan SEMUA kalimat sumber menjadi 1 batch encoding ===
    # Sebelumnya: model.encode() dipanggil N kali (sekali per sumber) -> lambat.
    # Sekarang:   model.encode() dipanggil 1 kali untuk seluruh kalimat sumber.
    # Hasilnya IDENTIK secara matematis (cosine similarity per-pair tidak berubah).
    all_source_sentences = []
    source_map = []  # (source_url, local_index) untuk setiap kalimat
    for source_url, sentences in corpus_sentences.items():
        if not sentences:
            continue
        start_idx = len(all_source_sentences)
        all_source_sentences.extend(sentences)
        source_map.append((source_url, start_idx, start_idx + len(sentences)))
    
    if not all_source_sentences:
        return {}
    
    print(f"[!] Encoding {len(all_source_sentences)} source sentences from {len(source_map)} sources in 1 batch...")
    try:
        all_source_embeddings = model.encode(all_source_sentences, convert_to_tensor=True,
                                             batch_size=batch_size, show_progress_bar=False)
    except Exception as e:
        if "cuda" in str(e).lower():
            print(f"[!] CUDA Error saat encode sumber ({e}). Fallback otomatis ke CPU...")
            model = get_model(force_cpu=True)
            query_embeddings = model.encode(unmatched_sentences, convert_to_tensor=True, 
                                           batch_size=batch_size, show_progress_bar=False)
            all_source_embeddings = model.encode(all_source_sentences, convert_to_tensor=True,
                                                 batch_size=batch_size, show_progress_bar=False)
        else:
            raise e
    
    # Hitung cosine similarity SEKALI untuk seluruh matriks (query x all_sources)
    full_similarity_matrix = util.pytorch_cos_sim(query_embeddings, all_source_embeddings)
    
    semantic_matches = {}
    # Iris matriks per-sumber untuk atribusi yang benar
    for source_url, start_idx, end_idx in source_map:
        source_slice = full_similarity_matrix[:, start_idx:end_idx]
        source_sents = all_source_sentences[start_idx:end_idx]
        
        for query_idx, query_sent in enumerate(unmatched_sentences):
            max_similarity = torch.max(source_slice[query_idx]).item()
            
            if max_similarity >= threshold:
                best_match_idx = torch.argmax(source_slice[query_idx]).item()
                
                if query_idx not in semantic_matches:
                    semantic_matches[query_idx] = []
                
                semantic_matches[query_idx].append({
                    'source_url': source_url,
                    'matched_text': source_sents[best_match_idx],
                    'similarity_score': max_similarity,
                    'detection_method': 'semantic',
                    'original_sentence': query_sent
                })

    # Urutkan tiap daftar match per-kalimat berdasarkan skor tertinggi. Tanpa ini,
    # daftar tersusun urut dict sumber, sehingga matches[0] di pemanggil belum tentu
    # match terbaik (atribusi sumber & skor yang ditampilkan bisa salah).
    for query_idx in semantic_matches:
        semantic_matches[query_idx].sort(key=lambda m: m['similarity_score'], reverse=True)

    return semantic_matches