
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_mistralai import MistralAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL").strip('"') if os.getenv("QDRANT_URL") else None
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "jurisol-legal-embeddings"

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

embeddings_model = MistralAIEmbeddings(model="mistral-embed", mistral_api_key=os.getenv("MISTRAL_API_KEY"))

def parse_metadata_filters(query: str) -> tuple[str, dict]:
    """
    Parse metadata filters from the query string.
    Supported formats:
    'section': ['section', 'sec', 's'],
    'law_name': ['law', 'act', 'law_name', 'statute'],
    'title': ['title', 'heading', 'name']
    """
    metadata_filters = {}
    search_query = query        # Available metadata fields from our document store with enhanced mappings
    metadata_fields = {
        'section': ['section', 'sec', 's'],
        'law_name': ['law', 'act', 'law_name', 'statute'],
        'title': ['title', 'heading', 'name'],
        'chapter': ['chapter', 'chap', 'ch'],
        'section_desc': ['section_desc', 'description', 'desc', 'content'],
        'section_title': ['section_title', 'stitle'],
        'chapter_title': ['chapter_title', 'ctitle']
    }
    
    # Extract metadata filters
    for field_group, aliases in metadata_fields.items():
        for alias in aliases:
            # Look for patterns like "field:value" or "field=value"
            for separator in [':', '=']:
                pattern = f"{alias}{separator}(\\S+)"
                import re
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    value = matches[0].strip('"\'')
                    metadata_filters[field_group] = value
                    # Remove the filter from search query
                    search_query = re.sub(f"{alias}{separator}{matches[0]}", "", search_query)
    
    # Clean up search query
    search_query = " ".join(search_query.split())
    return search_query, metadata_filters

def search_indian_law_documents(query: str, max_results: int = 5, confidence_threshold: float = 0.0) -> str:
    """
    Search the Indian law vector store for relevant legal documents and provisions.
    Supports metadata filtering using field:value syntax.
    
    Examples:
    - "law:civil_procedure limitations"
    - "section:123 property"
    - "title:jurisdiction AND law:civil_procedure"
    
    Available metadata filters:
    - section: Search by section number (e.g., section:123)
    - law_name: Search by law/act name (e.g., law:civil_procedure)
    - title: Search by section title (e.g., title:jurisdiction)
    """

    import logging
    try:
        logging.info(f"[VectorSearch] Query: {query}")
        # Validate inputs
        if not query or not isinstance(query, str):
            logging.warning("[VectorSearch] Invalid query input.")
            return "Error: Query must be a non-empty string."
        if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
            max_results = 5
        if not isinstance(confidence_threshold, (int, float)) or confidence_threshold < 0 or confidence_threshold > 1:
            confidence_threshold = 0.0
        # Parse metadata filters from query
        search_query, metadata_filters = parse_metadata_filters(query)
        logging.info(f"[VectorSearch] Parsed search_query: {search_query}, metadata_filters: {metadata_filters}")
        # Prepare Qdrant filter for metadata filtering
        qdrant_filter = None
        if metadata_filters:
            should = []
            for field, value in metadata_filters.items():
                should.append(rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key=field,
                            match=rest.MatchValue(value=str(value))
                        )
                    ]
                ))
            qdrant_filter = rest.Filter(should=should) if should else None
        # Get embedding for the search query
        query_vector = embeddings_model.embed_query(search_query)
        # Perform similarity search with Qdrant using search (supports filtering)
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=max_results,
            with_payload=True,
            query_filter=qdrant_filter
        )
        logging.info(f"[VectorSearch] Raw Qdrant results: {results}")
        # Qdrant returns a list of ScoredPoint objects
        scored_results = []
        for r in results:
            payload = r.payload or {}
            content = payload.get('section_desc') or payload.get('section_title') or payload.get('title') or payload.get('text') or ''
            class DummyDoc:
                def __init__(self, payload, content):
                    self.metadata = payload
                    self.page_content = str(content)
            scored_results.append((DummyDoc(payload, content), r.score))
        results = sorted(scored_results, key=lambda x: x[1], reverse=True)
        logging.info(f"[VectorSearch] Scored results: {results}")
        if confidence_threshold > 0:
            results = [(doc, score) for doc, score in results if score >= confidence_threshold]
        if not results:
            logging.warning(f"[VectorSearch] No relevant legal documents found for query: '{query}'")
            return f"No relevant legal documents found for query: '{query}'. Try rephrasing your question or lowering the confidence threshold."
        formatted_output = []
        formatted_output.append(f"SEARCH QUERY: {query}")
        formatted_output.append(f"QUERY CONTEXT: {search_query}")
        if metadata_filters:
            formatted_output.append("METADATA FILTERS:")
            for field, value in metadata_filters.items():
                formatted_output.append(f"- {field}: {value}")
        formatted_output.append(f"\nSEARCH STATISTICS:")
        formatted_output.append(f"- Total matches found: {len(results)}")
        formatted_output.append(f"- Average relevance score: {sum(score for _, score in results) / len(results):.4f}")
        formatted_output.append(f"- Top relevance score: {results[0][1]:.4f}")
        formatted_output.append(f"\nFOUND {len(results)} RELEVANT LEGAL DOCUMENTS:\n")
        for i, (document, similarity_score) in enumerate(results, 1):
            formatted_output.append(f"--- DOCUMENT {i} ---")
            formatted_output.append(f"Similarity Score: {similarity_score:.4f}")
            if hasattr(document, 'metadata') and document.metadata:
                metadata_str = []
                for key, value in document.metadata.items():
                    if key and value:
                        metadata_str.append(f"{key.title()}: {value}")
                if metadata_str:
                    formatted_output.append(f"Source: {' | '.join(metadata_str)}")
            content = document.page_content.strip()
            section_desc = document.metadata.get('section_desc', '')
            if section_desc:
                formatted_output.append(f"Section Description:\n{section_desc}")
            formatted_output.append("Content:")
            if len(content) > 1500:
                truncate_point = content[:1500].rfind('.')
                if truncate_point == -1:
                    truncate_point = 1500
                content = content[:truncate_point + 1] + "... [Content truncated]"
            formatted_output.append(content)
            related_sections = document.metadata.get('related_sections', [])
            if related_sections:
                formatted_output.append(f"\nRelated Sections: {', '.join(related_sections)}")
            formatted_output.append("")
        formatted_output.append(f"--- SEARCH SUMMARY ---")
        formatted_output.append(f"Total documents found: {len(results)}")
        if results:
            formatted_output.append(f"Average similarity score: {sum(score for _, score in results) / len(results):.4f}")
            metadata_summary = {}
            for doc, _ in results:
                if hasattr(doc, 'metadata'):
                    for key, value in doc.metadata.items():
                        if key not in metadata_summary:
                            metadata_summary[key] = set()
                        metadata_summary[key].add(str(value))
            if metadata_summary:
                formatted_output.append("\nMETADATA SUMMARY:")
                for key, values in metadata_summary.items():
                    if len(values) <= 5:
                        formatted_output.append(f"- {key}: {', '.join(sorted(values))}")
                    else:
                        formatted_output.append(f"- {key}: {len(values)} unique values")
        return "\n".join(formatted_output)
    except Exception as e:
        logging.exception(f"[VectorSearch] Error searching legal documents: {str(e)}")
        return f"Error searching legal documents: {str(e)}. Please try again with a different query."
