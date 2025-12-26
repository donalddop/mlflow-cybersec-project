# Contributing Guide

Thank you for your interest in contributing to the AI-Driven Cybersecurity Signal Triage Platform!

## Development Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) package manager

### Local Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mlflow-project
```

2. Complete setup:
```bash
make setup
```

3. Start the web interface:
```bash
make web
```

## Making Changes

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

### Project Structure

- `src/scripts/`: Backend scripts for data processing and ML
- `src/web/`: Flask web application
- `config/`: Configuration files and Docker setup
- `k8s/`: Kubernetes deployment manifests
- `docs/`: Documentation

### Testing Your Changes

1. Run the ingestion pipeline:
```bash
make ingest
make embed
```

2. Test the web interface:
```bash
make web
# Visit http://localhost:8000
```

3. Train a model:
```bash
make train
# Check MLflow UI at http://localhost:5000
```

## Submitting Changes

### Pull Request Process

1. Fork the repository
2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

3. Make your changes and commit:
```bash
git add .
git commit -m "Add: description of your changes"
```

4. Push to your fork:
```bash
git push origin feature/your-feature-name
```

5. Open a Pull Request

### Commit Message Format

Use clear, descriptive commit messages:

- `Add: new feature or functionality`
- `Fix: bug fix`
- `Update: changes to existing features`
- `Refactor: code restructuring`
- `Docs: documentation changes`
- `Style: formatting, no code change`

Example:
```
Add: multi-user voting system with vote aggregation

- Implement cookie-based user tracking
- Add upvote/downvote counts to API
- Update UI to display vote counts
```

## Feature Requests

Have an idea? Open an issue with:

1. **Problem**: What problem does this solve?
2. **Solution**: Your proposed solution
3. **Alternatives**: Other approaches you considered
4. **Additional Context**: Screenshots, examples, etc.

## Bug Reports

Found a bug? Open an issue with:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: How to trigger the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, Docker version
6. **Logs**: Relevant error messages or logs

## Areas for Contribution

### High Priority

- [ ] n8n webhook integration
- [ ] Automated retraining pipeline
- [ ] Model performance monitoring
- [ ] Email/Slack notifications

### Medium Priority

- [ ] Active learning implementation
- [ ] API for inference service
- [ ] Advanced analytics dashboard
- [ ] User authentication system

### Good First Issues

- [ ] Add more RSS feed sources
- [ ] Improve UI/UX in web interface
- [ ] Add more comprehensive tests
- [ ] Improve documentation
- [ ] Add configuration validation

## Questions?

- Open a GitHub issue
- Check existing documentation in `/docs`
- Review the README.md

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
