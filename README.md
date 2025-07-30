# EduSmartAI - Educational RAG Chatbot

A Windows-native Flask web application that provides an intelligent educational assistant powered by Retrieval-Augmented Generation (RAG) using LlamaIndex and Google Gemini.

## 🎯 Features

- **ChatGPT-like Interface**: Modern web UI with real-time chat functionality
- **RAG-Powered Responses**: Answers based on your uploaded educational documents
- **Document Processing**: Automatic ingestion and indexing of PDF files
- **Multiple Query Types**: 
  - General Q&A
  - Document summaries
  - Concept comparisons
- **Windows Native**: Runs entirely on Windows without Docker or WSL
- **Real-time Chat**: HTMX-powered responsive interface
- **Admin Dashboard**: System monitoring and management
- **Scheduled Processing**: Windows Task Scheduler integration

## 🏗️ Architecture

```
Browser ↔ Flask REST/HTMX endpoints
│     ├─ Chat blueprint     (/chat, /history)
│     ├─ RAG blueprint      (/rag/query, /rag/summary)
│     ├─ File blueprint     (/upload, /download)
│     └─ Admin blueprint    (/admin, /health)
│
└─ Services Layer
      ├─ LlamaIndexService    (Vector store: Chroma/FAISS)
      ├─ ConversationService  (Chat history: SQLite)
      └─ PDFIngestionPipeline (Document processing)
```

## 📋 Prerequisites

### Required Software
1. **Python 3.11+** for Windows with "Add to PATH" enabled
2. **Visual Studio Build Tools 2022** with "C++ build tools" workload (for some dependencies)
3. **Git** for Windows (optional, for cloning)

### API Keys
- **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Quick Start

### 1. Clone or Download
```bash
git clone https://github.com/indu-shekhar/EduSmartAI.git
cd EduSmartAI
```

### 2. Create Virtual Environment
```cmd
py -m venv .venv
call .venv\Scripts\activate.bat
```

### 3. Install Dependencies
```cmd
pip install -r requirements.txt
```

### 4. Configure Environment
```cmd
copy .env.example .env
```

Edit `.env` file and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_ENV=development
PORT=8000
```

### 5. Add Documents
Place your PDF files in the `books/` directory:
```cmd
mkdir books
# Copy your PDF files to books/ directory
```

### 6. Build Index
```cmd
python ingest.py --refresh
```

### 7. Start Application
For development:
```cmd
.\scripts\run_dev.ps1
```

For production:
```cmd
waitress-serve --port=8000 "app:create_app()"
```

### 8. Access Application
Open your browser and navigate to: http://localhost:8000

## 📁 Project Structure

```
EduSmartAI/
├─ app/                          # Flask application
│  ├─ __init__.py               # App factory
│  ├─ config.py                 # Configuration
│  ├─ blueprints/               # Route handlers
│  │  ├─ chat.py               # Chat functionality
│  │  ├─ rag.py                # RAG operations
│  │  ├─ file.py               # File management
│  │  └─ admin.py              # Admin interface
│  ├─ services/                 # Business logic
│  │  ├─ llama_index_service.py # RAG core
│  │  ├─ pdf_ingestion.py      # Document processing
│  │  └─ conversation_service.py # Chat history
│  ├─ models/                   # Database models
│  │  └─ database.py           # SQLAlchemy models
│  ├─ templates/                # HTML templates
│  │  ├─ base.html             # Base template
│  │  ├─ chat.html             # Chat interface
│  │  └─ admin.html            # Admin dashboard
│  └─ static/                   # Static assets
│     ├─ css/custom.css        # Custom styles
│     └─ js/                   # JavaScript
├─ books/                       # PDF documents
├─ storage/                     # Vector database
├─ scripts/                     # Windows scripts
│  ├─ activate_venv.bat        # Activate environment
│  ├─ run_dev.ps1              # Development server
│  ├─ ingest.ps1               # Document processing
│  └─ schedule_reingest.xml    # Task scheduler
├─ ingest.py                    # CLI ingestion tool
├─ requirements.txt             # Dependencies
├─ .env.example                 # Environment template
└─ README.md                    # This file
```

## 🔧 Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `FLASK_ENV`: Environment mode (development/production)
- `PORT`: Server port (default: 8000)
- `EMBEDDING_DB`: Vector database type (chromadb/faiss)
- `VECTOR_DIR`: Vector storage directory (default: ./storage)
- `BOOKS_DIR`: Documents directory (default: ./books)
- `UPLOAD_FOLDER`: File upload directory

### Development vs Production
- **Development**: Use `.\scripts\run_dev.ps1` for hot reloading
- **Production**: Use waitress WSGI server

## 📚 Usage

### Adding Documents
1. Place PDF files in the `books/` directory
2. Run ingestion: `python ingest.py --refresh`
3. Documents are automatically processed and indexed

### Chat Interface
- **General Questions**: Ask anything about your documents
- **Summaries**: "Summarize chapter 5" or "Give me an overview of..."
- **Comparisons**: "Compare X and Y" or "What's the difference between..."
- **Citations**: Click "Sources" to see document references

### Admin Dashboard
- Access at `/admin` for system monitoring
- View processing status, metrics, and logs
- Trigger re-indexing and cleanup operations

## 🔄 Maintenance

### Manual Index Refresh
```cmd
python ingest.py --refresh        # Incremental update
python ingest.py --rebuild        # Complete rebuild
```

### Scheduled Processing
Set up automatic daily processing:
```cmd
# Import the scheduled task
schtasks /Create /XML scripts\schedule_reingest.xml /TN "EduSmartAI\DailyReindex"

# View scheduled tasks
schtasks /Query /TN "EduSmartAI\DailyReindex"
```

### Cleanup Old Data
```cmd
# Via admin interface or API
curl -X POST http://localhost:8000/admin/cleanup -d '{"days": 30}'
```

## 🛠️ Troubleshooting

### Common Issues

**1. Virtual Environment Activation Fails**
```cmd
# Enable PowerShell execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**2. Package Installation Fails**
```cmd
# Upgrade pip first
python -m pip install --upgrade pip
# Install Visual Studio Build Tools if needed
```

**3. Gemini API Errors**
- Verify API key is correct in `.env`
- Check API quota and billing in Google Cloud Console
- Ensure internet connectivity

**4. No Documents Found**
- Check PDF files are in `books/` directory
- Verify files are readable (not password-protected)
- Check file permissions

**5. Index Loading Fails**
```cmd
# Clear storage and rebuild
rmdir /s storage
python ingest.py --rebuild
```

### Debug Mode
Enable verbose logging:
```cmd
python ingest.py --verbose
.\scripts\run_dev.ps1 -RefreshIndex
```

Check logs:
- `ingest.log` - Document processing
- Flask console output - Application logs

## 🧪 Testing

### Manual Testing
1. Start the application
2. Upload a test PDF
3. Ask questions about the content
4. Verify citations and sources

### Automated Testing
```cmd
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest tests/
```

## 🔒 Security

### Best Practices
- Keep `.env` file secure and never commit it
- Use HTTPS in production
- Regularly update dependencies
- Monitor file uploads for malicious content
- Implement rate limiting for production

### API Key Security
- Store API keys in environment variables only
- Use separate keys for development and production
- Rotate keys regularly

## 📈 Performance

### Optimization Tips
- Use SSD storage for vector database
- Increase RAM for larger document collections
- Consider PostgreSQL + pgvector for production
- Implement caching for frequent queries

### Monitoring
- Check admin dashboard for system health
- Monitor response times and error rates
- Review processing logs regularly

## 🔮 Future Enhancements

- [ ] User authentication and multi-tenancy
- [ ] Audio responses with Windows SAPI
- [ ] OCR support for scanned documents
- [ ] Progressive Web App features
- [ ] PostgreSQL + pgvector support
- [ ] Advanced citation formatting
- [ ] Export chat conversations
- [ ] Mobile-responsive improvements

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Windows
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Create an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check this README and inline comments

## 🙏 Acknowledgments

- **LlamaIndex**: For the RAG framework
- **Google Gemini**: For the AI capabilities
- **Bootstrap**: For the UI components
- **HTMX**: For reactive web interactions
- **Flask**: For the web framework

---

**Made with ❤️ for Windows users who want powerful AI assistance without complex containerization.**
