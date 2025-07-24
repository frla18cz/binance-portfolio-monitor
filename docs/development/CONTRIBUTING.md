# Contributing to Binance Portfolio Monitor

We love your input! We want to make contributing to this project as easy and transparent as possible.

## 🚀 Quick Start for Contributors

1. **Fork the repo** and create your branch from `main`
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run tests**: `python -m pytest tests/ -v`
4. **Make your changes** and add tests
5. **Ensure tests pass** and coverage remains high
6. **Submit a pull request**

## 📋 Development Process

We use GitHub to host code, track issues and feature requests, and accept pull requests.

### Pull Requests
1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing style
6. Issue that pull request!

### Issues
We use GitHub issues to track public bugs and feature requests:

- **Bug Report**: Use the bug report template
- **Feature Request**: Use the feature request template
- **Documentation**: For documentation improvements

## 🧪 Testing Guidelines

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=api --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_benchmark_functions.py -v
```

### Writing Tests
- Write tests for all new functions
- Use descriptive test names
- Include edge cases and error scenarios
- Mock external APIs (Binance, Supabase)
- Maintain >70% test coverage

### Test Structure
```python
def test_function_name_scenario():
    """Test description of what this test validates."""
    # Arrange
    setup_data = create_test_data()
    
    # Act  
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected_value
```

## 📝 Code Style Guidelines

### Python Style
- Follow PEP 8
- Use meaningful variable names
- Add docstrings for functions and classes
- Type hints where appropriate
- Maximum line length: 100 characters

### Commit Messages
Follow the conventional commits format:
```
feat: add support for multiple benchmarks
fix: resolve datetime parsing bug  
docs: update setup guide with troubleshooting
test: add integration tests for account processing
refactor: simplify benchmark calculation logic
```

### Code Organization
- Keep functions focused and small
- Separate concerns (API, business logic, data access)
- Use dependency injection for testing
- Handle errors gracefully with proper logging

## 🛠️ Development Setup

### Prerequisites
- Python 3.13+
- Git
- Code editor (PyCharm, VS Code, etc.)

### Local Development
```bash
# Clone your fork
git clone https://github.com/your-username/binance-portfolio-monitor.git
cd binance-portfolio-monitor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Run tests to verify setup
python -m pytest tests/ -v
```

### PyCharm Setup
1. **Open Project**: File → Open → Select project folder
2. **Configure Interpreter**: 
   - Settings → Python Interpreter
   - Add → Existing Environment
   - Select `.venv/bin/python`
3. **Run Configuration**:
   - Run → Edit Configurations
   - Add → Python
   - Script path: `api/index.py`
   - Working directory: project root

## 🎯 Areas for Contribution

### High Priority
- **Web Dashboard**: React/Next.js frontend
- **Additional Benchmarks**: More sophisticated strategies
- **Performance Optimization**: Database queries, API caching
- **Error Handling**: More robust error recovery

### Medium Priority  
- **Alerting System**: Email/Slack notifications
- **Multi-Exchange**: Support for other exchanges
- **Risk Metrics**: Sharpe ratio, drawdown analysis
- **Mobile App**: React Native implementation

### Documentation
- **Tutorials**: Video guides, blog posts
- **Examples**: Sample configurations, use cases
- **API Documentation**: OpenAPI/Swagger specs
- **Translations**: Documentation in other languages

## 🐛 Bug Reports

Great bug reports include:

1. **Summary**: Clear, concise description
2. **Steps to reproduce**: Detailed reproduction steps
3. **Expected vs Actual**: What should happen vs what happens
4. **Environment**: OS, Python version, dependencies
5. **Logs**: Relevant error messages or logs
6. **Screenshots**: If applicable

Use this template:
```markdown
**Bug Summary**
Brief description of the issue

**Steps to Reproduce**
1. Step one
2. Step two  
3. Step three

**Expected Behavior**
What you expected to happen

**Actual Behavior** 
What actually happened

**Environment**
- OS: [e.g. macOS 14.0]
- Python: [e.g. 3.13.0]
- Browser: [if web-related]

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

Good feature requests include:

1. **Use Case**: Why is this needed?
2. **Solution**: Proposed implementation
3. **Alternatives**: Other approaches considered
4. **Impact**: Who benefits and how?

## 🔒 Security

- **DO NOT** commit API keys, passwords, or secrets
- **DO NOT** include real trading data in examples
- Report security vulnerabilities privately via email
- Use `.env.example` for configuration templates

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

### Our Pledge
We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement
Instances of abusive behavior may be reported by contacting the project team.

---

## 🙋‍♂️ Questions?

Don't hesitate to ask! You can:
- Open an issue with the "question" label
- Start a discussion in GitHub Discussions
- Contact the maintainers directly

**Thank you for contributing! 🚀**