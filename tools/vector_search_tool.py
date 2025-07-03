
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings

# Initialize vector store
vector_store = Chroma(
    embedding_function=MistralAIEmbeddings(model="mistral-embed"),
    persist_directory='./indian_law_vector_store',
    collection_name='indian_law_docs'
)

def parse_metadata_filters(query: str) -> tuple[str, dict]:
    """
    Parse metadata filters from the query string.
    Supported formats:
    'section': ['section', 'sec', 's'],
    'law_name': ['law', 'act', 'law_name', 'statute'],
    'title': ['title', 'heading', 'name']
    """
    metadata_filters = {}
    search_query = query
    
    # Available metadata fields from our document store
    metadata_fields = {
        'section': ['section', 'sec', 's'],
        'law_name': ['law', 'act', 'law_name', 'statute'],
        'title': ['title', 'heading', 'name']
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
    try:
        # Validate inputs
        if not query or not isinstance(query, str):
            return "Error: Query must be a non-empty string."
        
        if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
            max_results = 5
            
        if not isinstance(confidence_threshold, (int, float)) or confidence_threshold < 0 or confidence_threshold > 1:
            confidence_threshold = 0.0
        
        # Parse metadata filters from query
        search_query, metadata_filters = parse_metadata_filters(query)
        
        # Prepare where clause for metadata filtering
        where = {}
        
        # Process metadata filters
        for field, value in metadata_filters.items():
            if field == 'section':
                # Handle section numbers
                try:
                    where[field] = str(int(value))  # Convert to string as sections are stored as strings
                except ValueError:
                    where[field] = {"$regex": value, "$options": "i"}
            elif field == 'law_name':
                # Handle law names with flexible matching
                where[field] = {"$regex": value.replace('_', ' '), "$options": "i"}
            else:
                # Handle other fields with case-insensitive search
                where[field] = {"$regex": value, "$options": "i"}
        
        # Perform similarity search with metadata filtering
        try:
            if where:
                results = vector_store.similarity_search_with_relevance_scores(
                    search_query,
                    k=max_results,
                    where=where
                )
            else:
                results = vector_store.similarity_search_with_relevance_scores(
                    search_query,
                    k=max_results
                )
        except TypeError as e:
            # Fallback: try without 'where' if TypeError about multiple 'where' arguments
            if 'multiple values for keyword argument' in str(e):
                results = vector_store.similarity_search_with_relevance_scores(
                    search_query,
                    k=max_results
                )
            else:
                raise
        
        results = sorted(results, key=lambda x: x[1], reverse=True)
        
        # Filter by confidence threshold if specified
        if confidence_threshold > 0:
            results = [(doc, score) for doc, score in results if score >= confidence_threshold]
        
        # Check if any results found
        if not results:
            return f"No relevant legal documents found for query: '{query}'. Try rephrasing your question or lowering the confidence threshold."
        
        # Format results for LLM consumption
        formatted_output = []
        formatted_output.append(f"SEARCH QUERY: {query}")
        if metadata_filters:
            formatted_output.append("METADATA FILTERS:")
            for field, value in metadata_filters.items():
                formatted_output.append(f"- {field}: {value}")
        formatted_output.append(f"\nFOUND {len(results)} RELEVANT LEGAL DOCUMENTS:\n")
        
        for i, (document, similarity_score) in enumerate(results, 1):
            formatted_output.append(f"--- DOCUMENT {i} ---")
            formatted_output.append(f"Similarity Score: {similarity_score:.4f}")
            
            # Add metadata if available
            if hasattr(document, 'metadata') and document.metadata:
                metadata_str = []
                for key, value in document.metadata.items():
                    if key and value:  # Only include non-empty metadata
                        metadata_str.append(f"{key.title()}: {value}")
                if metadata_str:
                    formatted_output.append(f"Source: {' | '.join(metadata_str)}")
            
            # Add document content
            content = document.page_content.strip()
            if len(content) > 1000:  # Truncate very long content
                content = content[:1000] + "... [Content truncated]"
            
            formatted_output.append(f"Content:\n{content}")
            formatted_output.append("")  # Empty line for separation
        
        # Add usage summary
        formatted_output.append(f"--- SEARCH SUMMARY ---")
        formatted_output.append(f"Total documents found: {len(results)}")
        if results:
            formatted_output.append(f"Average similarity score: {sum(score for _, score in results) / len(results):.4f}")
            
            # Add metadata summary if present
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
                    if len(values) <= 5:  # Only show summary if the values are reasonably few
                        formatted_output.append(f"- {key}: {', '.join(sorted(values))}")
                    else:
                        formatted_output.append(f"- {key}: {len(values)} unique values")
        
        return "\n".join(formatted_output)
        
    except Exception as e:
        return f"Error searching legal documents: {str(e)}. Please try again with a different query."
