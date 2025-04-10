# Project Overview

This project integrates with Google Docs and Drive using the Google API Client Library for Python. It provides tools to manage Google Docs documents programmatically.

## Features

### Document Management Tools

- `get_document`: Retrieve a Google Doc by its ID
- `create_document`: Create a new Google Doc with a specified title and content
- `update_document_content`: Update a Google Doc with styled content

## Prerequisites

- Python 3.7 or higher
- Google Cloud project with API access enabled
- OAuth 2.0 credentials

## Setup

1. **Create a Google Cloud Project**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable Google Docs and Drive APIs

2. **Get OAuth 2.0 Credentials**

   - In Google Cloud Console, go to APIs & Services > Credentials
   - Click "Create Credentials" and select "OAuth client ID"
   - Save the JSON file as `credentials.json` in your project root

3. **Install Dependencies**

   ```bash
   uv add google-api-python-client
   uv add "mcp[cli]"
   ```

## Dependencies

- `google-api-python-client`: For interacting with Google APIs.
- `mcp`: For managing the Model Context Protocol.

## Usage

To use the tools provided by this project, you need to authenticate with Google APIs. Follow the instructions in the code to set up your credentials.

## Running the Server

To run the MCP server for Google Docs, execute the following command:

```bash
python google_docs.py
```

This will start the server and you should see a message indicating that the Google Docs MCP server is running.

## Debugging

1. **Server Logs**

   Enable debug logs by setting the environment variable:

   ```bash
   export LOG_LEVEL=debug
   ```

2. **Tool Testing**

   Test individual tools using the MCP CLI:

   ```bash
   mcp test google_docs.py --tool get_document
   ```

## Usage Examples

### Document Operations

```python
# Create a new document
await create_document(title="My Document", content="Hello, world!")

# Update document content
await update_document_content(document_id="doc123", content="Updated content")
```

## Response Format

All tools return responses in a consistent format:

```python
# Success response
{
    "success": True,
    "data": {...},  # or relevant success data
    "message": "Operation completed successfully"
}

# Error response
{
    "success": False,
    "error": "Error message details"
}
```

## Security Considerations

1. **OAuth Credentials**

   - Never commit your `credentials.json` to version control
   - Add it to `.gitignore`
   - Use environment variables in production

## Contributing

Contributions are welcome! Please follow the standard guidelines for contributing to open-source projects.

## Creating a `uv`-Managed Project

If you haven't created a `uv`-managed project yet, you can do so with the following commands:

```bash
uv init my-project
cd my-project
```

## Adding MCP to Dependencies

To add MCP to your project dependencies, use the following command:

```bash
uv add "mcp[cli]"
```

This command is for adding MCP to `uv`-managed Python projects. If you're not familiar with `uv`, please refer to the [uv documentation](https://docs.astral.sh/uv/).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and feature requests, please create an issue in the GitHub repository.
