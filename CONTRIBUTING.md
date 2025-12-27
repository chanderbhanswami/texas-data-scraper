# Contributing to Texas Data Scraper

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs from `logs/` directory

### Suggesting Features

1. Check if the feature has been suggested
2. Create a new issue with:
   - Clear use case
   - Expected behavior
   - Why this feature would be useful
   - Possible implementation approach

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit with clear message (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📋 Development Setup

```bash
# Clone your fork
git clone https://github.com/chanderbhanswami/texas-data-scraper.git
cd texas-data-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies including dev tools
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run setup
python setup_project.py

# Configure environment
cp config/.env.example .env
# Add your test API keys
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_socrata_api.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Test Your Changes
Before submitting PR, ensure:
- [ ] All tests pass
- [ ] New code has tests
- [ ] Code follows style guidelines
- [ ] Documentation updated

## 📝 Code Style

### Python Style Guide
- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions/classes
- Keep functions focused and small
- Use meaningful variable names

### Format Code
```bash
# Auto-format with black
black src/ scripts/ tests/

# Check with flake8
flake8 src/ scripts/ tests/

# Type checking with mypy
mypy src/
```

### Example Function
```python
def process_taxpayer_data(taxpayer_id: str, 
                          include_details: bool = True) -> Dict[str, Any]:
    """
    Process taxpayer data from multiple sources.
    
    Args:
        taxpayer_id: Taxpayer identification number
        include_details: Whether to include detailed information
        
    Returns:
        Dictionary containing processed taxpayer data
        
    Raises:
        ValueError: If taxpayer_id is invalid
    """
    # Implementation here
    pass
```

## 📚 Documentation

### Update Documentation When:
- Adding new features
- Changing existing functionality
- Adding new configuration options
- Adding new dependencies

### Documentation Files
- `README.md` - Main documentation
- `QUICK_START.md` - Quick start guide
- Inline code comments
- Docstrings in code

## 🌳 Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical fixes

## 📋 Commit Guidelines

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples
```bash
feat(scraper): add bulk download functionality

Add ability to download multiple datasets in parallel using async/await.
Includes progress tracking and error handling.

Closes #123

---

fix(api): handle rate limit errors correctly

Previously, rate limit errors would crash the scraper.
Now they are caught and handled with exponential backoff.

Fixes #456
```

## 🐛 Debugging

### Enable Debug Mode
```bash
# In .env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Check Logs
```bash
# View current log
tail -f logs/texas_scraper_$(date +%Y-%m-%d).log

# View errors
tail -f logs/errors_$(date +%Y-%m-%d).log
```

## 🎯 Areas Needing Contribution

### High Priority
- [ ] Additional dataset support
- [ ] Enhanced error recovery
- [ ] Performance optimizations
- [ ] Additional export formats
- [ ] Docker containerization

### Medium Priority
- [ ] Web interface
- [ ] Database integration
- [ ] Scheduled scraping
- [ ] Email notifications
- [ ] Data visualization

### Low Priority
- [ ] Additional test coverage
- [ ] Code documentation
- [ ] Performance benchmarks
- [ ] Example notebooks

## 📞 Getting Help

- Check documentation in `README.md`
- Review existing issues and PRs
- Ask questions in Issues with `question` label
- Check logs for error details

## ⚖️ Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inspiring community for all.

### Our Standards
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other unethical or unprofessional conduct

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions help make this project better for everyone. We appreciate your time and effort!

---

**Questions?** Open an issue with the `question` label.