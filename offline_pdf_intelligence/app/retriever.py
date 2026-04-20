"""
Query retrieval module for Offline PDF Intelligence.

Routes queries to appropriate handlers based on detected intent,
formats evidence-based responses, and extracts entities via regex.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from .indexer import BM25Indexer


# Question type detection patterns
QUESTION_PATTERNS = {
    'locate': [r'\bwhich page\b', r'\bon what page\b'],  # Check locate first (more specific)
    'find': [r'\bwhere\b', r'\bmention\b', r'\bfind\b'],
    'define': [r'\bwhat is\b', r'\bdefine\b', r'\bmeans\b', r':\s*$'],
    'extract': [r'\blist all\b', r'\bextract\b', r'\ball dates\b', r'\ball amounts\b'],
    'compare': [r'\bacross\b', r'\bcompare\b', r'\bbetween\b'],
    'list': [r'\blist\b', r'\ball sections\b', r'\bwhich pages?\b'],
    'checklist': [r'\bdoes.*include\b', r'\bdoes.*have\b', r'\bis there a\b'],
    'who': [r'\bwho\b'],
    'when': [r'\bwhen\b', r'\bdate\b', r'\bdated\b'],
    'where': [r'\bwhere\b'],
}

# Regex patterns for entity extraction
ENTITY_PATTERNS = {
    'dates': r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
    'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'amounts': r'\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:dollars?|USD|cents?)\b',
    'proper_nouns': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
    'phone_numbers': r'\b(?:\+1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
}


def detect_question_type(query: str) -> str:
    """
    Detect the type of question using heuristic pattern matching.
    
    Args:
        query: User's query string
        
    Returns:
        Detected question type (e.g., 'find', 'define', 'extract', etc.)
    """
    query_lower = query.lower()
    
    # Check for specific question types
    for qtype, patterns in QUESTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return qtype
    
    # Default to 'find' for general searches
    return 'find'


def extract_entities(text: str, query_type: str) -> Dict[str, List[str]]:
    """
    Extract relevant entities from text based on query type.
    
    Args:
        text: Text to extract entities from
        query_type: Type of query (for targeting extraction)
        
    Returns:
        Dict mapping entity types to lists of extracted values
    """
    entities = {}
    
    # Determine which patterns to apply based on query type
    if query_type in ['who', 'when', 'where', 'extract']:
        # Extract all entity types
        for entity_type, pattern in ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = list(set(matches))
    else:
        # For other queries, just extract dates and proper nouns
        for entity_type in ['dates', 'proper_nouns']:
            pattern = ENTITY_PATTERNS[entity_type]
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = list(set(matches))
    
    return entities


def highlight_matches(text: str, query: str) -> str:
    """
    Highlight query terms in text (for display purposes).
    
    Args:
        text: Original text
        query: Query string with terms to highlight
        
    Returns:
        Text with highlighted terms (using **markdown** style)
    """
    # Split query into terms
    terms = re.findall(r'"[^"]+"|\S+', query.lower())
    terms = [t.strip('"') for t in terms]
    
    result = text
    for term in terms:
        if len(term) > 2:  # Skip very short terms
            # Case-insensitive replacement with highlighting
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            result = pattern.sub(lambda m: f"**{m.group()}**", result)
    
    return result


class QueryRetriever:
    """
    Retrieves and formats search results based on query intent.
    
    All responses are evidence-based - direct excerpts from documents,
    never generated prose.
    """
    
    def __init__(self, bm25_indexer: BM25Indexer):
        """
        Initialize the query retriever.
        
        Args:
            bm25_indexer: BM25 indexer for searching
        """
        self.bm25 = bm25_indexer
    
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve search results for a query.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of result dicts with excerpt, metadata, and score
        """
        if not self.bm25.is_indexed:
            raise ValueError("BM25 index not built")
        
        # Search BM25 index
        results = self.bm25.search(query, k=k * 2)  # Get extra for filtering
        
        formatted_results = []
        for chunk_idx, score in results:
            chunk_info = self.bm25.get_chunk_info(chunk_idx)
            
            # Get the actual text
            if chunk_idx < len(self.bm25.corpus):
                text = self.bm25.corpus[chunk_idx]
            else:
                continue
            
            # Extract entities
            query_type = detect_question_type(query)
            entities = extract_entities(text, query_type)
            
            # Format the result
            formatted_results.append({
                'chunk_index': chunk_idx,
                'text': text,
                'highlighted_text': highlight_matches(text, query),
                'score': float(score),
                'pdf_path': chunk_info.get('pdf_path', ''),
                'page_number': chunk_info.get('page_number', 0),
                'section_heading': chunk_info.get('section_heading', ''),
                'entities': entities
            })
        
        return formatted_results[:k]
    
    def format_response(self, query: str, 
                        results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format a response based on results and query type.
        
        Args:
            query: Original query
            results: List of retrieved results
            
        Returns:
            Response dict with message, excerpts, and metadata
        """
        if not results:
            return {
                'message': "No direct evidence found for that question in the loaded documents. Try different keywords.",
                'excerpts': [],
                'query_type': detect_question_type(query),
                'suggestions': [
                    "Try using more specific keywords",
                    "Check spelling of key terms",
                    "Use simpler phrasing"
                ]
            }
        
        # Get top result
        top_result = results[0]
        score = top_result['score']
        
        # Determine response template based on score
        if score >= 0.70:
            prefix = f"Based on page {top_result['page_number']}"
            if top_result['section_heading']:
                prefix += f" ({top_result['section_heading']})"
            prefix += ", I found this:"
        elif score >= 0.40:
            prefix = f"Possibly relevant — from page {top_result['page_number']}:"
        else:
            prefix = f"Weak match from page {top_result['page_number']}:"
        
        # Build response
        response = {
            'message': prefix,
            'excerpts': [
                {
                    'text': r['text'],
                    'highlighted_text': r['highlighted_text'],
                    'page_number': r['page_number'],
                    'pdf_path': r['pdf_path'],
                    'section_heading': r.get('section_heading', ''),
                    'score': r['score'],
                    'entities': r.get('entities', {})
                }
                for r in results
            ],
            'query_type': detect_question_type(query),
            'total_results': len(results)
        }
        
        # Add special handling for certain query types
        query_type = response['query_type']
        
        if query_type == 'when' and results:
            # Collect all dates found
            all_dates = []
            for r in results:
                all_dates.extend(r.get('entities', {}).get('dates', []))
            if all_dates:
                response['extracted_dates'] = list(set(all_dates))
        
        if query_type == 'who' and results:
            # Collect proper nouns (potential names)
            all_names = []
            for r in results:
                all_names.extend(r.get('entities', {}).get('proper_nouns', []))
            if all_names:
                response['extracted_names'] = list(set(all_names))[:10]
        
        return response
    
    def handle_define_query(self, query: str) -> Dict[str, Any]:
        """
        Handle definition-type queries.
        
        Looks for patterns like "X means", "X is defined as", "X:".
        
        Args:
            query: The query (should be a definition request)
            
        Returns:
            Response dict
        """
        # Extract the term being defined
        patterns = [
            r'what is\s+(\w+(?:\s+\w+)*)',
            r'define\s+(\w+(?:\s+\w+)*)',
            r'(\w+(?:\s+\w+)*)\s+means',
        ]
        
        term = None
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                term = match.group(1)
                break
        
        if not term:
            return self.format_response(query, [])
        
        # Search for definition patterns
        definition_patterns = [
            rf'{term}\s+(?:is|means|refers to)\s+[^.]+',
            rf'"{term}"\s*:\s*[^.]+',
            rf'\b{term}\b[^.]*defined as[^.]+',
        ]
        
        # Search in corpus for definitions
        results = []
        for i, text in enumerate(self.bm25.corpus):
            for pattern in definition_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    chunk_info = self.bm25.get_chunk_info(i)
                    results.append({
                        'chunk_index': i,
                        'text': matches[0],
                        'highlighted_text': f"**{matches[0]}**",
                        'score': 0.8,
                        'pdf_path': chunk_info.get('pdf_path', ''),
                        'page_number': chunk_info.get('page_number', 0),
                        'section_heading': chunk_info.get('section_heading', ''),
                        'entities': {}
                    })
                    break
        
        return self.format_response(query, results[:3])
    
    def handle_checklist_query(self, query: str, 
                                patterns_lib: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle checklist/boolean queries.
        
        Checks if specific clauses or content exist in documents.
        
        Args:
            query: The query
            patterns_lib: Library of patterns to check against
            
        Returns:
            Response dict with yes/no answer and citations
        """
        results = []
        
        # Search for each pattern in the library
        for clause_name, pattern in patterns_lib.items():
            for i, text in enumerate(self.bm25.corpus):
                if re.search(pattern, text, re.IGNORECASE):
                    chunk_info = self.bm25.get_chunk_info(i)
                    results.append({
                        'clause': clause_name,
                        'found': True,
                        'text': text[:200] + '...' if len(text) > 200 else text,
                        'page_number': chunk_info.get('page_number', 0),
                        'pdf_path': chunk_info.get('pdf_path', '')
                    })
                    break
        
        if results:
            return {
                'answer': 'Yes',
                'clauses_found': [r['clause'] for r in results],
                'citations': results,
                'message': f"Found {len(results)} matching clause(s):"
            }
        else:
            return {
                'answer': 'No',
                'clauses_found': [],
                'citations': [],
                'message': "No matching clauses found in the loaded documents."
            }
