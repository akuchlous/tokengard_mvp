# Flask AWS App

A simple Flask application ready for deployment to AWS with a custom domain.

## Features

- 🚀 Modern, responsive landing page
- ✅ Comprehensive test suite
- 🛠️ Makefile for easy development workflow
- 📱 Mobile-friendly design
- 🔍 Health check endpoint
- 🎨 Beautiful gradient design

## Quick Start

### 1. Setup Development Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# On Windows: venv\Scripts\activate

# Install dependencies
make install
```

### 2. Run the Application

```bash
# Start Flask app locally
make run

# Visit http://localhost:5000 in your browser
```

### 3. Run Tests

```bash
# Run all tests
make test

# Run all checks (lint + test)
make check
```

### Semantic Cache (LLM Proxy)

The LLM proxy uses a semantic cache backed by embeddings to return cached responses for prompts that are meaningfully similar, not just exact string matches.

- Model: `SentenceTransformer('all-MiniLM-L6-v2')`
- Similarity: cosine similarity with threshold 0.89
- Behavior:
  - On each request, we embed the prompt text and compare with cached embeddings per user.
  - If any cached prompt has cosine similarity ≥ 0.89, we return the cached response immediately and mark the response as from cache.
  - Otherwise, we call the LLM, then store the prompt, its embedding, and the response.

Install requirements including sentence-transformers:

```bash
pip install -r requirements.txt
```

Notes:
- The embedding model is loaded once lazily on first use inside the process.
- Analytics and logs include cache hit rates and cost savings; when semantic hits occur, we log the similarity score.

### Token Counting & Cost Estimation

Token counting uses OpenAI's tiktoken with model-aware encodings. Per-1k pricing is configured in `pricing.json`.

- Module: `app/utils/token_utils.py`
- Functions:
  - `count_tokens(text, model)` → token count using tiktoken
  - `estimate_cost(token_count, model, is_output=False)` → USD cost using `pricing.json`
- Proxy response includes metadata:

```json
{
  "success": true,
  "data": {
    "status": "success",
    "message": "Request processed successfully",
    "tokens": {
      "input_tokens": 12,
      "output_tokens": 24,
      "total_tokens": 36
    },
    "estimated_cost": {
      "input": 0.000018,
      "output": 0.000048,
      "total": 0.000066
    }
  }
}
```

## Available Make Commands

- `make help` - Show all available commands
- `make install` - Install dependencies
- `make run` - Run Flask app locally
- `make test` - Run tests
- `make clean` - Clean up cache files
- `make lint` - Check code style
- `make format` - Format code
- `make check` - Run all checks
- `make prod-run` - Run with gunicorn (production-like)

## Project Structure

```
flask-aws-app/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Makefile           # Development commands
├── test_app.py        # Test suite
├── templates/          # HTML templates
│   └── index.html     # Landing page
└── static/            # Static assets
    └── css/
        └── style.css  # Stylesheets
```

## Testing

The app includes comprehensive tests covering:
- Home page loading
- Health endpoint
- Content validation
- Error handling
- HTML structure

Run tests with: `make test`

## Next Steps: AWS Deployment

This app is ready for AWS deployment with:
1. S3 bucket for static hosting
2. CloudFront for CDN
3. Route 53 for custom domain
4. SSL certificate

## Development Workflow

1. **Local Development**: `make run` → test at localhost:5000
2. **Testing**: `make test` → verify functionality
3. **Code Quality**: `make check` → lint + test
4. **Deploy**: Ready for AWS deployment

## Requirements

- Python 3.8+
- Flask 3.0.0
- pytest for testing
- gunicorn for production
