# Reference: API Mockup Adapter Design

This guide explains how to design and implement configurable mock adapters for third-party services (LLMs, Headless AI Agents, etc.) to optimize development cost and speed.

## Core Concept

The system should allow switching between a `mock` provider and `live` providers using a single environment variable. Both providers must implement the same interface to ensure the application logic remains identical regardless of the provider being used.

## Configuration Strategy

Use a single environment variable for each service category.

```env
# Example .env configuration
AGENT_CLI_PROVIDER=mock  # Options: mock, claude, gemini, codex
```

## Implementation Steps

### 1. Define the Interface (Abstract Base Class)

Create an abstract base class that defines all required methods for the service.

```python
class IAIAgentAdapter(ABC):
    @abstractmethod
    async def execute_command(self, command: str, context: dict) -> AsyncIterator[str]:
        """Execute a command and stream the output."""
        pass
```

### 2. Implement the Mock Provider

The mock provider should simulate realistic behavior, including success, failure, and latency scenarios.

```python
class MockAIAdapter(IAIAgentAdapter):
    async def execute_command(self, command: str, context: dict) -> AsyncIterator[str]:
        yield "Starting mock execution...\n"
        # Simulate small delay
        await asyncio.sleep(0.5) 
        yield f"Mock output for: {command}\n"
        yield "Execution completed successfully.\n"
```

### 3. Implement Live Providers

Create specific adapters for each real-world provider.

```python
class ClaudeLiveAdapter(IAIAgentAdapter):
    async def execute_command(self, command: str, context: dict) -> AsyncIterator[str]:
        # Real implementation using Claude CLI or API
        ...
```

### 4. Implement the Provider Factory

Use a factory function to instantiate the correct adapter based on the environment configuration.

```python
def get_ai_adapter() -> IAIAgentAdapter:
    provider = os.getenv("AGENT_CLI_PROVIDER", "mock")
    if provider == "mock":
        return MockAIAdapter()
    elif provider == "claude":
        return ClaudeLiveAdapter()
    # Add other providers...
    return MockAIAdapter() # Safe default
```

## Mock Scenarios to Support

Ensure the Mock Adapter can simulate these scenarios to test the UI/Frontend resilience:

| Scenario | Trigger | Mock Behavior |
| :--- | :--- | :--- |
| **Standard Success** | Default | Immediate start, consistent output flow. |
| **Slow Network** | Config/Param | Add delays between stream chunks. |
| **Service Error** | Config/Param | Throw exceptions or return error codes. |
| **Interruption** | Cancel Signal | Handle clean shutdown of the stream. |

```