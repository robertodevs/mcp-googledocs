from google_docs import process_inline_formatting
import json

def test_bold_formatting():
    """Test the process_inline_formatting function with bold text."""
    # Test line with bold formatting
    test_line = "**Name:** ______________________________  **Date:** ________________"
    current_index = 1
    
    # Call the function
    requests, new_index = process_inline_formatting(test_line, current_index)
    
    # Print the results
    print(f"Input text: '{test_line}'")
    print(f"Starting index: {current_index}")
    print(f"Ending index: {new_index}")
    print(f"Number of requests generated: {len(requests)}")
    
    # Print the formatted requests
    print("\n=== Generated Requests ===")
    for i, request in enumerate(requests):
        print(f"\nRequest {i+1}:")
        print(json.dumps(request, indent=2))
    
    # Check for bold text styling
    bold_styles = [r for r in requests if 'updateTextStyle' in r and r['updateTextStyle']['textStyle'].get('bold')]
    
    print("\n=== Style Analysis ===")
    print(f"Bold style requests: {len(bold_styles)}")
    
    if bold_styles:
        print("\n=== Bold Formatting Details ===")
        for i, style in enumerate(bold_styles):
            start = style['updateTextStyle']['range']['startIndex']
            end = style['updateTextStyle']['range']['endIndex']
            
            # Find corresponding text
            text_requests = [r for r in requests if 'insertText' in r]
            text_content = ""
            for tr in text_requests:
                text_idx = tr['insertText']['location']['index']
                text = tr['insertText']['text']
                if text_idx <= start < text_idx + len(text):
                    text_content = text
                    break
            
            print(f"Bold style {i+1}:")
            print(f"  Range: {start}-{end}")
            print(f"  Styled text: '{text_content}'")

if __name__ == "__main__":
    test_bold_formatting() 