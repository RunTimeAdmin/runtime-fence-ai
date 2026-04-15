# Contributing to $KILLSWITCH

Thank you for your interest in contributing to $KILLSWITCH!

## Code of Conduct

Be respectful. We're building safety tools for AI agents.

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include reproduction steps
4. Include system information

### Suggesting Features

1. Check existing feature requests
2. Use the feature request template
3. Explain the use case
4. Describe expected behavior

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`npm test` and `pytest`)
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add new risk assessment algorithm
fix: resolve memory leak in runtime guard
docs: update API reference
test: add unit tests for kill switch
```

### Code Style

- **TypeScript**: Follow ESLint configuration
- **Python**: Follow PEP 8, use Black formatter

### Testing

All PRs must:
- Pass existing tests
- Include tests for new features
- Maintain or improve code coverage

## Development Setup

```bash
# Clone
git clone https://github.com/RunTimeAdmin/runtime-fence-ai.git
cd runtime-fence-ai

# Install dependencies
npm install
pip install -r requirements.txt

# Run tests
npm test
pytest
```

## Security

If you find a security vulnerability, please email security@runtimefence.com instead of creating a public issue.

## Questions?

- Open a discussion on GitHub
- Check the [Wiki](https://github.com/RunTimeAdmin/runtime-fence-ai/wiki)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
