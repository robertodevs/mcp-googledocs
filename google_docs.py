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
    """Process inline formatting and return the requests and updated index."""
    import re
    requests = []
    line_parts = []
    current_pos = 0
    formatting_matches = []
    for match in re.finditer(r'\*\*(.+?)\*\*|__(.+?)__', line):
        text = match.group(1) if match.group(1) else match.group(2)
        formatting_matches.append({
            'start': match.start(),
            'end': match.end(),
            'text': text,
            'type': 'bold'
        })
    for match in re.finditer(r'\*([^*]+)\*|_([^_]+)_', line):
        text = match.group(1) if match.group(1) else match.group(2)
        formatting_matches.append({
            'start': match.start(),
            'end': match.end(),
            'text': text,
            'type': 'italic'
        })
    for match in re.finditer(r'\[(.+?)\]\((.+?)\)', line):
        text = match.group(1)
        url = match.group(2)
        formatting_matches.append({
            'start': match.start(),
            'end': match.end(),
            'text': text,
            'url': url,
            'type': 'link'
        })
    formatting_matches.sort(key=lambda m: m['start'])
    i = 0
    while i < len(formatting_matches) - 1:
        if formatting_matches[i]['end'] > formatting_matches[i+1]['start']:
            formatting_matches.pop(i+1)
        else:
            i += 1
    for i, match in enumerate(formatting_matches):
        if match['start'] > current_pos:
            line_parts.append({
                'text': line[current_pos:match['start']],
                'type': 'normal'
            })
        line_parts.append({
            'text': match['text'],
            'type': match['type'],
            'url': match.get('url')
        })
        current_pos = match['end']
    if current_pos < len(line):
        line_parts.append({
            'text': line[current_pos:],
            'type': 'normal'
        })
    if not line_parts:
        line_parts.append({
            'text': line,
            'type': 'normal'
        })
    line_parts.append({
        'text': '\n',
        'type': 'normal'
    })
    for part in line_parts:
        text = part['text']
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': text
            }
        })
        if part['type'] == 'bold':
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
        elif part['type'] == 'italic':
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
        elif part['type'] == 'link':
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(text)
                    },
                    'textStyle': {
                        'link': {
                            'url': part['url']
                        }
                    },
                    'fields': 'link'
                }
            })
        current_index += len(text)
    return requests, current_index




def markdown_to_docs_requests(markdown_text: str) -> List[Dict[str, Any]]:
    """Convert markdown text to Google Docs API batchUpdate requests."""
    import re
    requests = []
    current_index = 1
    blocks = re.split(r'\n{2,}', markdown_text)
    for block in blocks:
        lines = block.split('\n')
        code_block_match = re.match(r'^```(\w*)\n(.*?)\n```$', block, re.DOTALL)
        if code_block_match:
            block_requests, current_index = process_code_block(block, current_index)
            requests.extend(block_requests)
            continue
        is_list = all(re.match(r'^\s*[\*\-\+]|\d+\.', line) for line in lines if line.strip())
        if is_list and lines:
            list_requests, current_index = process_list_block(lines, current_index)
            requests.extend(list_requests)
            continue
        header_requests, current_index = process_header(lines[0], current_index)
        requests.extend(header_requests)
        for line in lines[1:]:
            inline_requests, current_index = process_inline_formatting(line, current_index)
            requests.extend(inline_requests)
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