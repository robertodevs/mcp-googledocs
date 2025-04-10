from typing import Any, Dict, List, Optional, Callable
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

def markdown_to_docs_requests(markdown_text: str) -> List[Dict[str, Any]]:
    """Convert markdown text to Google Docs API batchUpdate requests.
    
    This function parses common markdown elements and creates the appropriate
    Google Docs API requests to replicate that formatting in a Google Doc.
    
    Args:
        markdown_text: The markdown text to convert
    
    Returns:
        A list of request objects for the batchUpdate method
    """
    import re
    
    requests = []
    current_index = 1  # Start at index 1 (after the initial position)
    
    # Process the markdown in blocks to handle complex elements like lists and code blocks
    blocks = re.split(r'\n{2,}', markdown_text)
    
    # Special handling for the last line with *Good luck!*
    last_line = markdown_text.strip().split('\n')[-1]
    if last_line.strip() == '*Good luck!*':
        has_good_luck = True
    else:
        has_good_luck = False
    
    for block in blocks:
        lines = block.split('\n')
        
        # Check if it's a code block (indented by 4 spaces or ```language code ```)
        code_block_match = re.match(r'^```(\w*)\n(.*?)\n```$', block, re.DOTALL)
        if code_block_match:
            # Extract code and language
            language = code_block_match.group(1)
            code = code_block_match.group(2)
            
            # Insert code text
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': code + "\n\n"
                }
            })
            
            # Apply code style (monospace font)
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
            
            current_index += len(code) + 2  # +2 for the newlines
            continue
        
        # Check if it's a list block
        is_list = all(re.match(r'^\s*[\*\-\+]|\d+\.', line) for line in lines if line.strip())
        if is_list and lines:
            for line in lines:
                # Check for ordered list
                ordered_match = re.match(r'^\s*(\d+)\.\s+(.+)$', line)
                # Check for unordered list
                unordered_match = re.match(r'^\s*[\*\-\+]\s+(.+)$', line)
                
                if ordered_match:
                    number = ordered_match.group(1)
                    text = ordered_match.group(2) + "\n"
                    
                    # Insert list item text
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': text
                        }
                    })
                    
                    # Apply numbered list style
                    requests.append({
                        'createParagraphBullets': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text) - 1  # Exclude the newline
                            },
                            'bulletPreset': 'NUMBERED_DECIMAL'
                        }
                    })
                    
                    current_index += len(text)
                
                elif unordered_match:
                    text = unordered_match.group(1) + "\n"
                    
                    # Insert list item text
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': text
                        }
                    })
                    
                    # Apply bullet list style
                    requests.append({
                        'createParagraphBullets': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text) - 1  # Exclude the newline
                            },
                            'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                        }
                    })
                    
                    current_index += len(text)
                
                else:
                    # Just a blank line or non-list line
                    requests.append({
                        'insertText': {
                            'location': {'index': current_index},
                            'text': line + "\n"
                        }
                    })
                    current_index += len(line) + 1
            
            # Add extra newline after list block
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': "\n"
                }
            })
            current_index += 1
            continue
        
        # Regular block of text (paragraphs, headers, etc.)
        for line in lines:
            if not line.strip():  # Empty line
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': "\n"
                    }
                })
                current_index += 1
                continue
            
            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2) + "\n"
                
                # Insert the header text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': text
                    }
                })
                
                # Apply heading style
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
                continue
            
            # Process inline formatting for bold, italic, links, etc.
            line_parts = []
            current_pos = 0
            
            # Find all formatting elements in the line
            formatting_matches = []
            # Bold: **text** or __text__
            for match in re.finditer(r'\*\*(.+?)\*\*|__(.+?)__', line):
                text = match.group(1) if match.group(1) else match.group(2)
                formatting_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': text,
                    'type': 'bold'
                })
            
            # Italic: *text* or _text_
            for match in re.finditer(r'\*([^*]+)\*|_([^_]+)_', line):
                text = match.group(1) if match.group(1) else match.group(2)
                formatting_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': text,
                    'type': 'italic'
                })
            
            # Links: [text](url)
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
            
            # Sort formatting matches by start position
            formatting_matches.sort(key=lambda m: m['start'])
            
            # Simple check to remove overlapping matches (taking the first one)
            i = 0
            while i < len(formatting_matches) - 1:
                if formatting_matches[i]['end'] > formatting_matches[i+1]['start']:
                    formatting_matches.pop(i+1)
                else:
                    i += 1
            
            # Process the line with formatting
            for i, match in enumerate(formatting_matches):
                # Add text before the formatting
                if match['start'] > current_pos:
                    line_parts.append({
                        'text': line[current_pos:match['start']],
                        'type': 'normal'
                    })
                
                # Add the formatted text
                line_parts.append({
                    'text': match['text'],
                    'type': match['type'],
                    'url': match.get('url')
                })
                
                current_pos = match['end']
            
            # Add remaining text
            if current_pos < len(line):
                line_parts.append({
                    'text': line[current_pos:],
                    'type': 'normal'
                })
            
            # If no formatting found, add the whole line
            if not line_parts:
                line_parts.append({
                    'text': line,
                    'type': 'normal'
                })
            
            # Add a newline at the end
            line_parts.append({
                'text': '\n',
                'type': 'normal'
            })
            
            # Insert all parts with appropriate styling
            for part in line_parts:
                text = part['text']
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': text
                    }
                })
                
                # Apply styling based on part type
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
        
        # Add an extra newline between blocks
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "\n"
            }
        })
        current_index += 1
    
    # Special handling for "Good luck!" text with italic
    if has_good_luck:
        good_luck_text = "Good luck!"
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': good_luck_text
            }
        })
        
        # Apply italic style
        requests.append({
            'updateTextStyle': {
                'range': {
                    'startIndex': current_index,
                    'endIndex': current_index + len(good_luck_text)
                },
                'textStyle': {
                    'italic': True
                },
                'fields': 'italic'
            }
        })
        
        # Add final newline
        current_index += len(good_luck_text)
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': "\n"
            }
        })
    
    return requests

if __name__ == "__main__":
    try:
        # Run the MCP server
        print("🚀 Starting Google Docs MCP server...")
        mcp.run(transport='sse')
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)