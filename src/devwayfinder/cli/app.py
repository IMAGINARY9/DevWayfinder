"""CLI application for DevWayfinder."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from devwayfinder.core.exceptions import DevWayfinderError
from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.providers import create_provider, load_provider_config, supported_providers

app = typer.Typer(
    name="devwayfinder",
    help="AI-Powered Developer Onboarding Generator",
    add_completion=False,
)

console = Console()
SUPPORTED_PROVIDER_HELP = ", ".join(supported_providers())


@app.command()
def generate(
    path: str = typer.Argument(
        ".",
        help="Path to project to analyze",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
    model_provider: str = typer.Option(
        "openai_compat",
        "--model-provider",
        help=f"LLM provider ({SUPPORTED_PROVIDER_HELP})",
    ),
    model_name: str | None = typer.Option(
        None,
        "--model-name",
        help="Model identifier",
    ),
    base_url: str | None = typer.Option(
        None,
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
        "--verbose",
        "-v",
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
        "--verbose",
        "-v",
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
        "openai_compat",
        "--provider",
        help=f"Provider to test ({SUPPORTED_PROVIDER_HELP})",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="API base URL",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model to test",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        envvar="DEVWAYFINDER_API_KEY",
        help="API key for remote providers",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Timeout in seconds for health and completion checks",
    ),
    no_completion: bool = typer.Option(
        False,
        "--no-completion",
        help="Only run the health check",
    ),
) -> None:
    """Test connection to LLM provider."""
    asyncio.run(
        _test_model_async(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
            no_completion=no_completion,
        )
    )


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


async def _test_model_async(
    *,
    provider: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    timeout: float,
    no_completion: bool,
) -> None:
    """Run provider health and completion checks."""
    config = load_provider_config(
        provider=provider,
        model_name=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
    llm_provider = create_provider(config)

    console.print(f"[bold blue]DevWayfinder[/bold blue] — Testing {llm_provider.name}")
    console.print(f"Endpoint: {config.resolved_base_url() or 'n/a'}")
    console.print(f"Model: {config.model_name or 'provider default'}")

    try:
        health = await llm_provider.health_check()
        if not health.healthy:
            console.print(f"[red]Provider unhealthy:[/red] {health.message}")
            raise typer.Exit(code=1)

        console.print(f"[green]Provider is healthy[/green] — {health.message}")
        if health.latency_ms is not None:
            console.print(f"Latency: {health.latency_ms:.1f} ms")
        if health.model_info:
            console.print(f"Model info: {health.model_info}")

        if no_completion:
            return

        sample_context = SummarizationContext(
            module_name="devwayfinder.providers.factory",
            docstrings=["Creates a configured model provider for onboarding summaries."],
            signatures=["create_provider(config: ProviderConfig) -> ModelProvider"],
            imports=["devwayfinder.providers.ollama", "devwayfinder.providers.openai"],
            exports=["create_provider", "supported_providers"],
        )
        summary = await llm_provider.summarize(sample_context)
        if summary:
            console.print("[green]Completion check passed[/green]")
            console.print(f"Preview: {summary[:160]}")
        else:
            console.print("[yellow]Completion returned an empty response[/yellow]")
            raise typer.Exit(code=1)
    except DevWayfinderError as exc:
        console.print(f"[red]{exc.__class__.__name__}:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]ConfigurationError:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        close_method = getattr(llm_provider, "close", None)
        if callable(close_method):
            await close_method()
