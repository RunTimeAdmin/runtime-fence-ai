# Installation Guide

Install $KILLSWITCH to add emergency stop capabilities to your AI agents.

## Requirements

- Python 3.10 or higher
- pip package manager

## Quick Install (pip)

```bash
pip install runtime-fence
```

## Install from Source

```bash
git clone https://github.com/RunTimeAdmin/ai-agent-killswitch.git
cd ai-agent-killswitch/packages/python
pip install -e .
```

## Platform-Specific Installation

### Windows

1. Download and run `install_fence.bat`
2. A desktop shortcut will be created
3. Runtime Fence will auto-start with Windows

### macOS

```bash
chmod +x install_fence.sh
./install_fence.sh
```

The fence will be added to your Login Items.

### Linux

```bash
chmod +x install_fence.sh
./install_fence.sh
```

A `.desktop` file will be created for your application menu.

## Verify Installation

```bash
fence version --check
fence test
```

## Uninstall

### Windows
```bash
pip uninstall runtime-fence
```

### Mac/Linux
```bash
./uninstall_fence.sh
pip uninstall runtime-fence
```

## Next Steps

- [Quick Start](Quick-Start)
- [Configuration](Configuration)
