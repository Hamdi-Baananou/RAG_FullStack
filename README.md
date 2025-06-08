# RAG Fullstack Application

This is a fullstack application for document processing and information extraction using RAG (Retrieval-Augmented Generation).

## Features

- PDF document processing with text extraction
- Web scraping for supplier data
- Two-stage extraction process (web + PDF fallback)
- Real-time metrics and evaluation
- Export functionality for results and metrics

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn
- Playwright (for web scraping)

## Setup

### Backend Setup

1. Create and activate a virtual environment:
```bash
cd backend
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Unix/MacOS
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Create a `.env` file in the backend directory with the following variables:
```
MISTRAL_API_KEY=your_mistral_api_key
OPENAI_API_KEY=your_openai_api_key
```

5. Start the backend server:
```bash
uvicorn main:app --reload --port 8000
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Usage

1. Open the application in your browser
2. Upload PDF documents
3. Optionally enter a part number for web scraping
4. Click "Process Documents" to start extraction
5. View results and metrics
6. Export results as CSV or metrics as JSON

## API Documentation

Once the backend is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Backend Structure
- `main.py`: FastAPI application entry point
- `config.py`: Application configuration
- `routers/`: API endpoints
- `services/`: Core business logic
- `utils/`: Utility functions
- `prompts/`: LLM prompts

### Frontend Structure
- `pages/`: Vue.js pages
- `components/`: Reusable Vue components
- `composables/`: Vue composables
- `public/`: Static assets

## License

MIT 