from typing import Any, Dict, List, Optional, Callable, Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest
from mcp.server.fastmcp import FastMCP
import os.path
import pickle

# Initialize FastMCP server
mcp = FastMCP("google-docs")

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

def get_credentials() -> Credentials:
    """Get valid user credentials from storage.
    
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    """
    creds = None
    # Use the user's home directory for token storage
    token_path = os.path.join(os.path.expanduser('~'), '.google-docs-token.pickle')
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_docs_service():
    """Get the Google Docs service instance."""
    creds = get_credentials()
    return build('docs', 'v1', credentials=creds)

def get_drive_service():
    """Get the Google Drive service instance."""
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

# Document Management Tools
@mcp.tool()
async def get_document(document_id: str) -> Dict[str, Any]:
    """Get a Google Doc by its ID.
    
    Args:
        document_id: The ID of the document to retrieve
    """
    try:
        service = get_docs_service()
        
        doc = service.documents().get(documentId=document_id).execute()
        
        return {
            "success": True,
            "document_id": doc.get('documentId'),
            "title": doc.get('title'),
            "body": doc.get('body'),
            "revision_id": doc.get('revisionId')
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def create_document(title: str, content: str = "") -> Dict[str, Any]:
    """Create a new Google Doc with the specified title and content.
    
    Args:
        title: The title of the new document
        content: Optional initial content for the document
    """
    try:
        # First create the document in Drive
        drive_service = get_drive_service()
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.document'
        }
        file = drive_service.files().create(body=file_metadata).execute()
        
        # If content is provided, update the document with styled content
        if content:
            docs_service = get_docs_service()
            requests = markdown_to_docs_requests(content)
            docs_service.documents().batchUpdate(
                documentId=file['id'],
                body={'requests': requests}
            ).execute()
        
        return {
            "success": True,
            "document_id": file['id'],
            "title": title,
            "message": "Document created successfully",
            "url": f"https://docs.google.com/document/d/{file['id']}/edit"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def update_document_content(document_id: str, content: str) -> Dict[str, Any]:
    """Update a Google Doc with the specified content, converting markdown to styled text.
    
    Args:
        document_id: The ID of the document to update
        content: Markdown content to insert and style
    """
    try:
        # Get the current document to determine if we need to clear it first
        docs_service = get_docs_service()
        document = docs_service.documents().get(documentId=document_id).execute()
        
        requests = []
        
        # If document has content beyond the initial empty paragraph, delete it first
        if document.get('body', {}).get('content', None) and len(document['body']['content']) > 1:
            # Delete all content except the first paragraph end marker
            requests.append({
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': document['body']['content'][-1]['endIndex'] - 1
                    }
                }
            })
        
        # Convert markdown and add the styled content
        style_requests = markdown_to_docs_requests(content)
        requests.extend(style_requests)
        
        # Execute the batch update
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        return {
            "success": True,
            "document_id": document_id,
            "message": "Document updated successfully with styled content"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def process_code_block(block: str, current_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """Process a code block and return the requests and updated index."""
    import re
    requests = []
    code_block_match = re.match(r'^```(\w*)\n(.*?)\n```$', block, re.DOTALL)
    if code_block_match:
        code = code_block_match.group(2)
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': code + "\n\n"
            }
        })
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': current_index,
                    'endIndex': current_index + len(code)
                },
                'textStyle': {
                    'fontFamily': 'Consolas',
                    'backgroundColor': {'color': {'rgbColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}}}
                },
                'fields': 'fontFamily,backgroundColor'
            }
        })
        current_index += len(code) + 2
    return requests, current_index


def process_list_block(lines: List[str], current_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """Process a list block and return the requests and updated index."""
    import re
    requests = []
    for line in lines:
        ordered_match = re.match(r'^\s*(\d+)\.\s+(.+)$', line)
        unordered_match = re.match(r'^\s*[\*\-\+]\s+(.+)$', line)
        if ordered_match:
            text = ordered_match.group(2) + "\n"
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text) - 1
                    },
                    'bulletPreset': 'NUMBERED_DECIMAL_ALPHA_ROMAN'
                }
            })
            current_index += len(text)
        elif unordered_match:
            text = unordered_match.group(1) + "\n"
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text) - 1
                    },
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
            current_index += len(text)
        else:
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': line + "\n"
                }
            })
            current_index += len(line) + 1
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': "\n"
        }
    })
    current_index += 1
    return requests, current_index


def process_header(line: str, current_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """Process a header line and return the requests and updated index."""
    import re
    requests = []
    header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if header_match:
        level = len(header_match.group(1))
        text = header_match.group(2) + "\n"
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': text
            }
        })
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': current_index,
                    'endIndex': current_index + len(text)
                },
                'paragraphStyle': {
                    'namedStyleType': f'HEADING_{level}'
                },
                'fields': 'namedStyleType'
            }
        })
        current_index += len(text)
    return requests, current_index


def process_inline_formatting(line: str, current_index: int) -> Tuple[List[Dict[str, Any]], int]:
    """Process inline formatting for a line of text and return the requests and updated index."""
    import re
    requests = []
    
    # Define common patterns  
    bold_pattern = r'\*\*(.+?)\*\*|__(.+?)__'
    italic_pattern = r'\*([^*]+)\*|_([^_]+)_'
    
    # Check if there is formatting in the line
    has_bold = re.search(bold_pattern, line) is not None
    has_italic = re.search(italic_pattern, line) is not None
    
    # If no formatting, just return the line as is
    if not has_bold and not has_italic:
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': line + '\n'
            }
        })
        return requests, current_index + len(line) + 1
    
    # Handle bold text first - replace it with plain text and add formatting
    if has_bold:
        # Find first bold section
        bold_match = re.search(bold_pattern, line)
        
        # Get the text content, position, etc.
        text = bold_match.group(1) or bold_match.group(2)
        start = bold_match.start()
        end = bold_match.end()
        
        # Add any text before the bold part
        if start > 0:
            prefix = line[:start]
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': prefix
                }
            })
            current_index += len(prefix)
        
        # Add the bold text
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': text
            }
        })
        
        # Apply bold formatting
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': current_index,
                    'endIndex': current_index + len(text)
                },
                'textStyle': {
                    'bold': True
                },
                'fields': 'bold'
            }
        })
        
        current_index += len(text)
        
        # Process the remainder of the line recursively
        if end < len(line):
            remaining_line = line[end:]
            remaining_requests, current_index = process_inline_formatting(remaining_line, current_index)
            requests.extend(remaining_requests)
            return requests, current_index
        else:
            # End of line, add newline
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            return requests, current_index + 1
    
    # Handle italic text next if no bold text was found
    if has_italic:
        # Find first italic section
        italic_match = re.search(italic_pattern, line)
        
        # Get the text content, position, etc.
        text = italic_match.group(1) or italic_match.group(2)
        start = italic_match.start()
        end = italic_match.end()
        
        # Add any text before the italic part
        if start > 0:
            prefix = line[:start]
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': prefix
                }
            })
            current_index += len(prefix)
        
        # Add the italic text
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': text
            }
        })
        
        # Apply italic formatting
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': current_index,
                    'endIndex': current_index + len(text)
                },
                'textStyle': {
                    'italic': True
                },
                'fields': 'italic'
            }
        })
        
        current_index += len(text)
        
        # Process the remainder of the line recursively
        if end < len(line):
            remaining_line = line[end:]
            remaining_requests, current_index = process_inline_formatting(remaining_line, current_index)
            requests.extend(remaining_requests)
            return requests, current_index
        else:
            # End of line, add newline
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            return requests, current_index + 1
    
    # Should never reach here, but just in case
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': line + '\n'
        }
    })
    return requests, current_index + len(line) + 1


def markdown_to_docs_requests(markdown_text: str) -> List[Dict[str, Any]]:
    """Convert markdown text to Google Docs API batchUpdate requests."""
    import re
    requests = []
    current_index = 1
    
    # Split text into blocks (paragraphs)
    blocks = re.split(r'\n{2,}', markdown_text)
    
    for i, block in enumerate(blocks):
        lines = block.split('\n')
        
        # Process code blocks
        code_block_match = re.match(r'^```(\w*)\n(.*?)\n```$', block, re.DOTALL)
        if code_block_match:
            block_requests, current_index = process_code_block(block, current_index)
            requests.extend(block_requests)
            continue
        
        # Check if the first line is a header
        is_header = False
        if lines and lines[0].strip():
            header_match = re.match(r'^(#{1,6})\s+(.+)$', lines[0])
            if header_match:
                is_header = True
                header_requests, current_index = process_header(lines[0], current_index)
                requests.extend(header_requests)
                lines = lines[1:]  # Remove the header line since it's been processed
        
        # More accurate list detection:
        # A list item starts with: number + period + space, or asterisk/dash/plus + space
        list_pattern = r'^\s*(\d+\.\s+|\*\s+|-\s+|\+\s+)'
        is_list = False
        
        if len(lines) > 0 and all(line.strip() == '' or re.match(list_pattern, line) for line in lines):
            is_list = True
            list_requests, current_index = process_list_block(lines, current_index)
            requests.extend(list_requests)
            continue
            
        # Now process each line in the paragraph for formatting
        for j, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '\n'
                    }
                })
                current_index += 1
                continue
                
            # Check for formatting in this line
            has_formatting = bool(re.search(r'\*\*|\*|__|_|\[.+?\]\(.+?\)', line))
            
            if has_formatting:
                inline_requests, current_index = process_inline_formatting(line, current_index)
                requests.extend(inline_requests)
            else:
                # Just insert the text without formatting
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': line + '\n'
                    }
                })
                current_index += len(line) + 1
        
        # Add extra newline after block
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "\n"
            }
        })
        current_index += 1
        
    return requests

if __name__ == "__main__":
    try:
        # Run the MCP server
        print("🚀 Starting Google Docs MCP server...")
        mcp.run(transport='sse')
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)