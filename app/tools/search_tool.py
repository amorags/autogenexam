from typing import Annotated
import json

def search_web(query: Annotated[str, "The search query to look up"]) -> str:
    """
    Search the web using DuckDuckGo for information.
    Returns a JSON string with search results.
    
    Tips for better results:
    - Be specific: include location, data source (OECD, statistics)
    - Add keywords: "statistics", "data", "official"
    - Include time ranges in the query
    """
    try:
        # Try the new package name first, fallback to old one
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            # Increase max_results to get better chances of finding good data
            results = list(ddgs.text(query, max_results=8))
            
        if not results:
            return json.dumps({
                "error": "No results found", 
                "query": query,
                "suggestion": "Try a more specific query with keywords like 'statistics', 'data', or 'OECD'"
            })
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append({
                "position": i,
                "title": result.get("title", ""),
                "snippet": result.get("body", ""),
                "url": result.get("href", "")
            })
        
        return json.dumps({
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "query": query,
            "suggestion": "Try rephrasing your search query"
        })