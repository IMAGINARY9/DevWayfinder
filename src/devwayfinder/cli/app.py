"""CLI application for DevWayfinder."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from devwayfinder.analyzers import GraphBuilder, StructureAnalyzer
from devwayfinder.cli.progress import create_generation_tracker
from devwayfinder.core.exceptions import DevWayfinderError
from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.generators import GenerationConfig, GuideGenerator
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
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        envvar="DEVWAYFINDER_API_KEY",
        help="API key for LLM provider",
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
    asyncio.run(
        _generate_async(
            path=path,
            output=output,
            model_provider=model_provider,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            no_llm=no_llm,
            no_graph=no_graph,
            no_metrics=no_metrics,
            verbose=verbose,
        )
    )


async def _generate_async(
    *,
    path: str,
    output: str | None,
    model_provider: str,
    model_name: str | None,
    base_url: str | None,
    api_key: str | None,
    no_llm: bool,
    no_graph: bool,
    no_metrics: bool,
    verbose: bool,
) -> None:
    """Run the full generation pipeline."""
    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {project_path}")
        raise typer.Exit(code=1)

    if not project_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {project_path}")
        raise typer.Exit(code=1)

    console.print(Panel.fit(
        f"[bold blue]DevWayfinder[/bold blue]\n"
        f"Generating onboarding guide for: [cyan]{project_path.name}[/cyan]",
        border_style="blue",
    ))

    # Build LLM provider if needed
    providers = []
    if not no_llm:
        try:
            config = load_provider_config(
                provider=model_provider,
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )
            provider = create_provider(config)
            providers.append(provider)

            if verbose:
                console.print(f"[dim]Using provider: {provider.name}[/dim]")
                console.print(f"[dim]Endpoint: {config.resolved_base_url() or 'default'}[/dim]")
        except ValueError as exc:
            console.print(f"[yellow]Warning:[/yellow] Could not configure LLM: {exc}")
            console.print("[yellow]Falling back to heuristic mode.[/yellow]")
            no_llm = True

    try:
        with create_generation_tracker(console) as tracker:
            # Create generator
            gen_config = GenerationConfig(
                use_llm=not no_llm,
                providers=providers,
                include_mermaid=not no_graph,
            )
            generator = GuideGenerator(
                project_path=project_path,
                config=gen_config,
            )

            # Define progress callback
            def on_progress(phase: str, status: str, detail: str) -> None:
                """Handle progress updates from generator."""
                if status == "start":
                    tracker.start_phase(phase, detail)
                elif status == "progress":
                    tracker.update_progress(phase, detail)
                elif status == "complete":
                    tracker.complete_phase(phase, detail)
                elif status == "failed":
                    tracker.fail_phase(phase, detail)
                elif status == "skipped":
                    tracker.skip_phase(phase, detail)

            # Run generation with progress tracking
            result = await generator.generate(progress_callback=on_progress)

        # Output guide
        markdown = result.guide.to_markdown()

        if output:
            output_path = Path(output)
            output_path.write_text(markdown, encoding="utf-8")
            console.print(f"\n[green]Guide written to:[/green] {output_path}")
        else:
            console.print("\n" + "─" * 60)
            console.print(markdown)

        # Show summary
        console.print("\n" + "─" * 60)
        console.print(f"[green]✓[/green] Generated guide with {len(result.guide.sections)} sections")
        console.print(f"[green]✓[/green] Analyzed {result.modules_analyzed} modules")
        console.print(f"[green]✓[/green] Generation time: {result.total_time_seconds:.2f}s")

        if result.errors:
            console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for error in result.errors[:5]:
                console.print(f"  [yellow]•[/yellow] {error}")
            if len(result.errors) > 5:
                console.print(f"  [dim]... and {len(result.errors) - 5} more[/dim]")

    except DevWayfinderError as exc:
        console.print(f"\n[red]{exc.__class__.__name__}:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        for provider in providers:
            close_method = getattr(provider, "close", None)
            if callable(close_method):
                await close_method()


@app.command()
def analyze(
    path: str = typer.Argument(
        ".",
        help="Path to project to analyze",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON instead of formatted text",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Analyze project structure without generating guide."""
    asyncio.run(_analyze_async(path=path, output_json=output_json, verbose=verbose))


async def _analyze_async(*, path: str, output_json: bool, verbose: bool) -> None:
    """Run the analysis pipeline."""
    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {project_path}")
        raise typer.Exit(code=1)

    if not project_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {project_path}")
        raise typer.Exit(code=1)

    console.print(Panel.fit(
        f"[bold blue]DevWayfinder[/bold blue]\n"
        f"Analyzing: [cyan]{project_path.name}[/cyan]",
        border_style="blue",
    ))

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Structure analysis
            task = progress.add_task("[cyan]Analyzing project structure...", total=None)
            structure_analyzer = StructureAnalyzer()
            structure = await structure_analyzer.analyze(project_path)
            progress.update(task, description="[green]Structure analysis complete!")

            # Build dependency graph
            task2 = progress.add_task("[cyan]Building dependency graph...", total=None)
            graph_builder = GraphBuilder()
            project, graph = await graph_builder.build(project_path)
            progress.update(task2, description="[green]Dependency graph complete!")

        if output_json:
            import json
            result = {
                "project_name": project.name,
                "primary_language": structure.primary_language,
                "build_system": structure.build_system,
                "package_manager": structure.package_manager,
                "entry_points": [str(ep.path) for ep in project.entry_points],
                "file_count": len(structure.source_files),
                "graph": {
                    "node_count": graph.node_count,
                    "edge_count": graph.edge_count,
                },
            }
            console.print(json.dumps(result, indent=2))
        else:
            # Display structure info
            console.print("\n")

            # Project info table
            table = Table(title=f"Project: {project.name}", show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("Primary Language", structure.primary_language or "Unknown")
            table.add_row("Build System", structure.build_system or "Not detected")
            table.add_row("Package Manager", structure.package_manager or "Not detected")
            table.add_row("Files Analyzed", str(len(structure.source_files)))
            table.add_row("Modules Found", str(graph.node_count))
            table.add_row("Dependencies", str(graph.edge_count))

            console.print(table)

            # Entry points
            entry_points = project.entry_points
            if entry_points:
                console.print("\n[bold]Entry Points:[/bold]")
                for ep in entry_points[:10]:
                    console.print(f"  [green]→[/green] {ep.path.name}")
                if len(entry_points) > 10:
                    console.print(f"  [dim]... and {len(entry_points) - 10} more[/dim]")

            # Top-level directories (use relative paths)
            top_dirs = set()
            for p in structure.source_files:
                try:
                    rel_path = p.relative_to(project_path)
                    if len(rel_path.parts) > 1:
                        top_dirs.add(rel_path.parts[0])
                except ValueError:
                    pass
            if top_dirs:
                console.print("\n[bold]Top-Level Structure:[/bold]")
                tree = Tree(f"[cyan]{project_path.name}[/cyan]")
                for d in sorted(top_dirs)[:15]:
                    tree.add(f"[blue]{d}/[/blue]")
                if len(top_dirs) > 15:
                    tree.add(f"[dim]... and {len(top_dirs) - 15} more[/dim]")
                console.print(tree)

            # Graph info
            if verbose:
                console.print("\n[bold]Core Modules:[/bold]")
                core_modules = graph.get_core_modules(threshold=3)
                for module in core_modules[:10]:
                    deps = len(graph.get_dependencies(module.path))
                    dependents = len(graph.get_dependents(module.path))
                    console.print(f"  [cyan]{module.path.name}[/cyan]: {deps} deps, {dependents} dependents")

        console.print("\n[green]✓[/green] Analysis complete!")

    except DevWayfinderError as exc:
        console.print(f"\n[red]{exc.__class__.__name__}:[/red] {exc}")
        raise typer.Exit(code=1) from exc


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
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Configuration template (auto-detected if not specified)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
    list_templates: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List available templates",
    ),
) -> None:
    """Initialize .devwayfinder configuration directory."""
    from devwayfinder.cli.templates import (
        TEMPLATES,
        initialize_config,
    )

    # List templates if requested
    if list_templates:
        console.print("[bold]Available configuration templates:[/bold]\n")
        for name, tmpl in TEMPLATES.items():
            indicators = ", ".join(tmpl.file_indicators) if tmpl.file_indicators else "any project"
            console.print(f"  [cyan]{name}[/cyan] — {tmpl.description}")
            console.print(f"    [dim]Detected by: {indicators}[/dim]\n")
        return

    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {project_path}")
        raise typer.Exit(code=1)

    if not project_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {project_path}")
        raise typer.Exit(code=1)

    console.print(
        f"[bold blue]DevWayfinder[/bold blue] — Initializing configuration\n"
        f"Project: [cyan]{project_path}[/cyan]"
    )

    try:
        config_path, template_used = initialize_config(
            project_path,
            template_name=template,
            force=force,
        )

        console.print("\n[green]✓[/green] Configuration initialized!")
        console.print(f"  Template: [cyan]{template_used}[/cyan]")
        console.print(f"  Config: [dim]{config_path}[/dim]")
        console.print("\nEdit [cyan].devwayfinder/config.yaml[/cyan] to customize settings.")

    except FileExistsError as exc:
        console.print(f"\n[yellow]Warning:[/yellow] {exc}")
        console.print("Use [cyan]--force[/cyan] to overwrite existing configuration.")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"\n[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


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
