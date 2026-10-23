# create-max-framework

Scaffold a new [MAX/MSP Claude Code Framework](https://github.com/taylorbrook/MAX-MSP_CC_Framework) project with a single command.

## Usage

```bash
npx create-max-framework my-project
cd my-project
claude
```

## What it does

- Downloads the latest framework release from GitHub
- Sets up the project directory with all skills, commands, object database, and Python library
- Initializes a git repository and prints getting-started instructions
- Checks Python 3.10+, the Python packages below and git, and warns about anything missing

## Prerequisites

- [Node.js](https://nodejs.org/) 16+ (for running this installer)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for using the framework)
- [MAX 9](https://cycling74.com/products/max) (for opening and testing generated patches)
- [Python 3.10+](https://www.python.org/) (for the validation and editing engine)
- [git](https://git-scm.com/) (every patch save is committed)
- numpy, scipy and pytest (the DSP simulation, smoke tests and the DSP pre-flight gate; validation works without them). Install them from the project directory:

  ```bash
  python3 -m pip install -r requirements-dev.txt
  ```

Run `npx create-max-framework --check-deps` to repeat the checks without installing.

## Links

- [Main repository](https://github.com/taylorbrook/MAX-MSP_CC_Framework)
- [Technical documentation](https://github.com/taylorbrook/MAX-MSP_CC_Framework/blob/main/TECHNICAL.md)
