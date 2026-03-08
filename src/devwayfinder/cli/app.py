"""CLI application for DevWayfinder."""

import typer
from rich.console import Console

app = typer.Typer(
    name="devwayfinder",
    help="AI-Powered Developer Onboarding Generator",
    add_completion=False,
)

console = Console()


@app.command()
def generate(
    path: str = typer.Argument(
        ".",
        help="Path to project to analyze",
    ),
    output: str | None = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: stdout)",
    ),
    model_provider: str = typer.Option(
        "ollama",
        "--model-provider",
        help="LLM provider (ollama, openai, heuristic)",
    ),
    model_name: str = typer.Option(
        "mistral:7b",
        "--model-name",
        help="Model identifier",
    ),
    base_url: str = typer.Option(
        "http://localhost:11434",
        "--base-url",
        help="Model API base URL",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Use heuristic mode (no LLM)",
    ),
    no_graph: bool = typer.Option(
        False,
        "--no-graph",
        help="Exclude dependency graph from output",
    ),
    no_metrics: bool = typer.Option(
        False,
        "--no-metrics",
        help="Exclude complexity metrics from output",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Generate onboarding guide for a project."""
    console.print(f"[bold blue]DevWayfinder[/bold blue] — Generating guide for: {path}")
    console.print("[yellow]Note: Full implementation coming in MVP 1[/yellow]")
    # TODO: Implement full generation pipeline


@app.command()
def analyze(
    path: str = typer.Argument(
        ".",
        help="Path to project to analyze",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Analyze project structure without generating guide."""
    console.print(f"[bold blue]DevWayfinder[/bold blue] — Analyzing: {path}")
    console.print("[yellow]Note: Full implementation coming in MVP 1[/yellow]")
    # TODO: Implement analysis pipeline


@app.command("test-model")
def test_model(
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Provider to test (ollama, openai)",
    ),
    base_url: str = typer.Option(
        "http://localhost:11434",
        "--base-url",
        help="API base URL",
    ),
    model: str = typer.Option(
        "mistral:7b",
        "--model",
        help="Model to test",
    ),
) -> None:
    """Test connection to LLM provider."""
    console.print(f"[bold blue]DevWayfinder[/bold blue] — Testing {provider} at {base_url}")
    console.print("[yellow]Note: Full implementation coming in MVP 1[/yellow]")
    # TODO: Implement provider health check


@app.command()
def init(
    path: str = typer.Argument(
        ".",
        help="Path to initialize",
    ),
) -> None:
    """Initialize .devwayfinder configuration directory."""
    console.print(f"[bold blue]DevWayfinder[/bold blue] — Initializing config at: {path}")
    console.print("[yellow]Note: Full implementation coming in MVP 2[/yellow]")
    # TODO: Implement config initialization


@app.command()
def version() -> None:
    """Show DevWayfinder version."""
    from devwayfinder import __version__
    console.print(f"DevWayfinder version {__version__}")


if __name__ == "__main__":
    app()
