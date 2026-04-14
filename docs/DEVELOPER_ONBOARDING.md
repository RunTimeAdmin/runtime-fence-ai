# $KILLSWITCH Protocol - Developer Onboarding Guide

## Welcome to $KILLSWITCH Protocol

Thank you for joining our mission to make AI agents safe and controllable. This guide will help you get started contributing to Runtime Fence and the broader $KILLSWITCH Protocol ecosystem.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding the Architecture](#understanding-the-architecture)
3. [Development Environment Setup](#development-environment-setup)
4. [Your First Contribution](#your-first-contribution)
5. [Development Workflow](#development-workflow)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation Standards](#documentation-standards)
8. [Community Resources](#community-resources)
9. [Common Tasks](#common-tasks)
10. [Getting Help](#getting-help)

---

## Quick Start

### Prerequisites

Before you start, make sure you have:

- **Node.js** (v18 or higher)
- **Python** (v3.11 or higher)
- **Git** (latest version)
- **Docker** (for containerized testing)
- **A code editor** (VS Code recommended with extensions)

### Install in 5 Minutes

```bash
# Clone the repository
git clone https://github.com/RunTimeAdmin/ai-agent-killswitch.git
cd ai-agent-killswitch

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
cd sdk/typescript
npm install

# Run tests
pytest tests/
npm test
```

### Your First Run

Create a file `first_run.py`:

```python
from runtime_fence import RuntimeFence

# Initialize Runtime Fence
fence = RuntimeFence(
    api_key="your_api_key_here",  # Get from runtimefence.com
    environment="development"
)

# Test a simple action
result = fence.validate_action(
    agent_id="test_agent_001",
    action_type="file_read",
    parameters={
        "path": "/etc/passwd"
    }
)

print(f"Action allowed: {result['allowed']}")
print(f"Risk score: {result['risk_score']}")
print(f"Reason: {result['reason']}")
```

Run it:

```bash
python first_run.py
```

Expected output:

```
Action allowed: False
Risk score: 85
Reason: Critical system file access blocked
```

---

## Understanding the Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent Layer                           │
│  (Your application, chatbot, autonomous agent, etc.)        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ API Call
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   SDK Layer                                  │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   Python SDK    │         │  TypeScript SDK │           │
│  │                 │         │                 │           │
│  │ - Action API    │         │ - Action API    │           │
│  │ - Risk Scoring  │         │ - Risk Scoring  │           │
│  │ - Event Hooks   │         │ - Event Hooks   │           │
│  └─────────────────┘         └─────────────────┘           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ REST API / WebSocket
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              Runtime Fence Engine                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Python Middleware (Core Engine)              │   │
│  │                                                      │   │
│  │  • Action Validation (<1ms response)                │   │
│  │  • Risk Scoring (0-100 scale)                       │   │
│  │  • Behavioral Analysis                              │   │
│  │  • Transaction Simulation                           │   │
│  │  • Emergency Kill Switch                            │   │
│  └────────────────────┬────────────────────────────────┘   │
│                       │                                      │
│                       │ Smart Contract Calls                 │
│                       ↓                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Smart Contract Layer (Solana)              │   │
│  │                                                      │   │
│  │  • AIGuard.sol (Main contract)                       │   │
│  │  • Allowance Module                                  │   │
│  │  • Target Whitelist                                  │   │
│  │  • Kill Switch                                       │   │
│  │  • Blacklist System                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Data Storage
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Data Layer                                   │
│  • PostgreSQL (user data, audit logs)                      │
│  • Redis (caching, rate limiting)                          │
│  • IPFS (document storage)                                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Runtime Fence Engine

**Location**: `/runtime_fence/`

**Purpose**: Core validation engine that analyzes AI agent actions in real-time.

**Key Files**:
- `runtime_guard.py` - Main guard class
- `risk_scoring.py` - Risk assessment algorithm
- `action_validator.py` - Action validation logic
- `behavioral_analysis.py` - Behavioral pattern detection
- `emergency_controls.py` - Kill switch and emergency actions

#### 2. Smart Contracts

**Location**: `/contracts/`

**Purpose**: On-chain governance and security controls.

**Key Files**:
- `AIGuard.sol` - Main contract
- `AllowanceModule.sol` - Permission management
- `KillSwitch.sol` - Emergency controls

#### 3. SDKs

**Location**: `/sdk/`

**Purpose**: Easy integration for developers.

**Key Files**:
- `sdk/python/` - Python SDK
- `sdk/typescript/` - TypeScript/Node.js SDK

#### 4. Tests

**Location**: `/tests/`

**Purpose**: Comprehensive test suite ensuring reliability.

**Test Stats**: 82/82 tests passing (17 Solidity + 65 Python)

---

## Development Environment Setup

### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub first
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-agent-killswitch.git
cd ai-agent-killswitch

# Add upstream remote
git remote add upstream https://github.com/RunTimeAdmin/ai-agent-killswitch.git
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Step 3: Set Up Node.js Environment

```bash
# Navigate to TypeScript SDK
cd sdk/typescript

# Install dependencies
npm install

# Build the SDK
npm run build

# Return to root directory
cd ../..
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
# Required variables:
# - API_KEY: Get from https://runtimefence.com
# - ENVIRONMENT: development | staging | production
# - LOG_LEVEL: debug | info | warning | error
```

### Step 5: Run Development Server

```bash
# Start the API server
python -m runtime_fence.api.server

# Or use the development server with auto-reload
uvicorn runtime_fence.api.server:app --reload
```

Server will start at: `http://localhost:8000`

### Step 6: Run Tests

```bash
# Run all Python tests
pytest tests/ -v

# Run specific test file
pytest tests/test_risk_scoring.py -v

# Run with coverage
pytest --cov=runtime_fence tests/

# Run Solidity tests
cd contracts
npm test
```

### Step 7: Verify Setup

```bash
# Run health check
python -c "from runtime_fence import RuntimeFence; print('Setup successful!')"
```

---

## Your First Contribution

### Choose Your Path

#### Path 1: Fix a Bug (Beginner)

1. Look for issues labeled `good first issue` or `bug`
2. Comment on the issue to claim it
3. Fix the bug
4. Add tests for your fix
5. Submit a pull request

#### Path 2: Add a Feature (Intermediate)

1. Check existing feature requests
2. Create an issue discussing your proposal
3. Get feedback from maintainers
4. Implement the feature
5. Write tests and documentation
6. Submit a pull request

#### Path 3: Improve Documentation (Beginner)

1. Find unclear or missing documentation
2. Improve the documentation
3. Submit a pull request

#### Path 4: Add Tests (Beginner)

1. Find code with low test coverage
2. Write comprehensive tests
3. Ensure all tests pass
4. Submit a pull request

### Example Contribution: Adding a New Action Type

**Scenario**: Add support for `database_query` action type

**Step 1: Update Action Types**

Edit `runtime_fence/action_validator.py`:

```python
class ActionType(Enum):
    """Supported AI agent action types"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK_REQUEST = "network_request"
    SYSTEM_COMMAND = "system_command"
    DATABASE_QUERY = "database_query"  # NEW
    # ... other types
```

**Step 2: Add Validation Logic**

```python
def validate_action(self, action_type: ActionType, parameters: dict) -> ValidationResult:
    # ... existing validation logic
    
    if action_type == ActionType.DATABASE_QUERY:
        return self._validate_database_query(parameters)

def _validate_database_query(self, params: dict) -> ValidationResult:
    """Validate database query actions"""
    
    dangerous_patterns = [
        'DROP TABLE',
        'DELETE FROM',
        'TRUNCATE',
        'GRANT ALL',
        'REVOKE ALL'
    ]
    
    query = params.get('query', '').upper()
    
    for pattern in dangerous_patterns:
        if pattern in query:
            return ValidationResult(
                allowed=False,
                risk_score=95,
                reason=f"Dangerous SQL pattern detected: {pattern}"
            )
    
    sensitive_tables = ['users', 'passwords', 'credit_cards', 'api_keys']
    
    table = params.get('table', '').lower()
    if table in sensitive_tables:
        return ValidationResult(
            allowed=False,
            risk_score=85,
            reason=f"Access to sensitive table blocked: {table}"
        )
    
    return ValidationResult(
        allowed=True,
        risk_score=20,
        reason="Database query validated"
    )
```

**Step 3: Add Tests**

Create `tests/test_database_query.py`:

```python
import pytest
from runtime_fence import RuntimeFence

def test_dangerous_sql_pattern():
    fence = RuntimeFence(api_key="test_key")
    
    result = fence.validate_action(
        agent_id="test_agent",
        action_type="database_query",
        parameters={
            "query": "DROP TABLE users",
            "table": "users"
        }
    )
    
    assert result['allowed'] == False
    assert result['risk_score'] >= 90

def test_safe_query():
    fence = RuntimeFence(api_key="test_key")
    
    result = fence.validate_action(
        agent_id="test_agent",
        action_type="database_query",
        parameters={
            "query": "SELECT * FROM products WHERE id = 1",
            "table": "products"
        }
    )
    
    assert result['allowed'] == True
    assert result['risk_score'] < 50
```

---

## Development Workflow

### Git Workflow

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, then commit
git add .
git commit -m "feat: description of your change"

# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `style`: Formatting
- `chore`: Maintenance

---

## Testing Guidelines

### Test Coverage Requirements

- **Minimum**: 80% code coverage
- **Target**: 90%+ code coverage
- All new features must have tests
- All bug fixes must have regression tests

### Running Tests

```bash
# Full test suite
pytest tests/ -v --cov=runtime_fence

# Specific module
pytest tests/test_risk_scoring.py -v

# With coverage report
pytest --cov=runtime_fence --cov-report=html tests/
```

---

## Getting Help

### Community Resources

- **GitHub Discussions**: Ask questions, share ideas
- **Wiki**: https://github.com/RunTimeAdmin/ai-agent-killswitch/wiki
- **Twitter**: @DeFiAuditCCIE

### Contact

- **Security Issues**: security@runtimefence.com
- **General Questions**: GitHub Discussions

---

## $KILLSWITCH Token

**Contract**: `56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon`

[Buy on Jupiter](https://jup.ag/tokens/56o8um92XU8QMr1FsSj4nkExEkgKe56PBTAMqCAzmoon)

### Token Holder Benefits

| Holdings | Discount | Governance |
|----------|----------|------------|
| 1,000+ | - | Vote on proposals |
| 10,000+ | 10% off | Vote on proposals |
| 100,000+ | 20% off | Vote on proposals |
| 1,000,000+ | 40% off | 2x voting power |

---

*"Because every AI needs an off switch."*
