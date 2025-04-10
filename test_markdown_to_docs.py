from google_docs import markdown_to_docs_requests
import json
import re

def test_markdown_to_docs():
    """Test the markdown_to_docs_requests function with a simple example."""
    # Test markdown with bold and italic formatting
    test_markdown = """# Test Heading

**This is bold text** and *this is italic text*.

Here's a paragraph with both **bold** and *italic* formatting.
"""
    
    # Debug the paragraphs
    paragraphs = test_markdown.split("\n\n")
    for i, paragraph in enumerate(paragraphs):
        print(f"Paragraph {i+1}: '{paragraph}'")
        has_formatting = bool(re.search(r'\*\*|\*|__|_|\[.+?\]\(.+?\)', paragraph))
        print(f"  Has formatting: {has_formatting}")
    
    # Call the function
    requests = markdown_to_docs_requests(test_markdown)
    
    # Print the results
    print(f"\nGenerated {len(requests)} requests")
    
    # Count request types
    req_types = {}
    for req in requests:
        req_type = list(req.keys())[0]
        req_types[req_type] = req_types.get(req_type, 0) + 1
    
    print("\n=== Request Types ===")
    for req_type, count in req_types.items():
        print(f"{req_type}: {count}")
    
    # Find text style requests
    text_styles = [r for r in requests if 'updateTextStyle' in r]
    
    print(f"\nFound {len(text_styles)} text style requests")
    
    # Print all requests for analysis
    print("\n=== All Requests ===")
    for i, req in enumerate(requests):
        print(f"\nRequest {i+1}:")
        print(json.dumps(req, indent=2))

if __name__ == "__main__":
    test_markdown_to_docs() 