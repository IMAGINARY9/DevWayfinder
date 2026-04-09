"""CLI application for DevWayfinder."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
import yaml
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from devwayfinder.analyzers import GraphBuilder, StructureAnalyzer
from devwayfinder.cli.console import create_console
from devwayfinder.cli.progress import create_generation_tracker
from devwayfinder.core.exceptions import DevWayfinderError
from devwayfinder.core.protocols import ModelProvider, SummarizationContext
from devwayfinder.generators import GenerationConfig, GenerationResult, GuideGenerator
from devwayfinder.providers import create_provider, load_provider_config, supported_providers
from devwayfinder.utils.tokens import TokenEstimate, estimate_cost
from devwayfinder.version import get_version

app = typer.Typer(
    name="devwayfinder",
    help="AI-Powered Developer Onboarding Generator",
    add_completion=False,
)

console = create_console()
SUPPORTED_PROVIDER_HELP = ", ".join(supported_providers())

QUALITY_PROFILES = ("deep", "balanced", "fast")

AUTO_PROVIDER_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("openai_compat", "http://127.0.0.1:11434/v1"),
    ("openai_compat", "http://127.0.0.1:11435/v1"),
    ("openai_compat", "http://127.0.0.1:1234/v1"),
    ("openai_compat", "http://127.0.0.1:5000/v1"),
    ("openai_compat", "http://127.0.0.1:8000/v1"),
    ("ollama", "http://localhost:11434"),
)


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
    quality: str = typer.Option(
        "deep",
        "--quality",
        help="Quality profile: deep, balanced, fast",
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Auto-probe local providers and use the first healthy endpoint",
    ),
    guide_template: str | None = typer.Option(
        None,
        "--guide-template",
        help="Path to guide template YAML (default: .devwayfinder/template.yaml)",
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
            quality=quality,
            auto=auto,
            guide_template=guide_template,
            verbose=verbose,
        )
    )


@app.command()
def guide(
    path: str = typer.Argument(
        ".",
        help="Path to project to analyze",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Guide output path (default: PATH/ONBOARDING_GUIDE.md)",
    ),
    quality: str = typer.Option(
        "deep",
        "--quality",
        help="Quality profile: deep, balanced, fast",
    ),
    auto: bool = typer.Option(
        True,
        "--auto/--manual",
        help="Auto-probe local providers (default: enabled)",
    ),
    model_name: str | None = typer.Option(
        None,
        "--model-name",
        help="Optional model identifier override",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Optional endpoint override",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        envvar="DEVWAYFINDER_API_KEY",
        help="API key for remote providers",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Force heuristic-only mode",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """Generate guide using the guided one-command workflow."""
    project_path = Path(path).resolve()
    default_output = project_path / "ONBOARDING_GUIDE.md"
    run_report = project_path / ".devwayfinder" / "run_report.md"

    asyncio.run(
        _generate_async(
            path=path,
            output=output or str(default_output),
            model_provider="openai_compat",
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            no_llm=no_llm,
            quality=quality,
            auto=auto,
            guide_template=None,
            verbose=verbose,
            run_report_path=str(run_report),
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
    quality: str,
    auto: bool,
    guide_template: str | None,
    verbose: bool,
    run_report_path: str | None = None,
) -> None:
    """Run the full generation pipeline."""
    project_path = Path(path).resolve()

    if not project_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {project_path}")
        raise typer.Exit(code=1)

    if not project_path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {project_path}")
        raise typer.Exit(code=1)

    project_excludes, include_hidden, config_path = _load_project_analysis_settings(project_path)
    merged_excludes = _merge_patterns(GenerationConfig().exclude_patterns, project_excludes)

    console.print(
        Panel.fit(
            f"[bold blue]DevWayfinder[/bold blue]\n"
            f"Generating onboarding guide for: [cyan]{project_path.name}[/cyan]",
            border_style="blue",
        )
    )

    if verbose and config_path is not None:
        console.print(f"[dim]Loaded analysis config: {config_path}[/dim]")

    try:
        quality_profile = _normalize_quality_profile(quality)
    except ValueError as exc:
        console.print(f"[red]ConfigurationError:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    effective_no_llm = no_llm or quality_profile == "fast"
    if quality_profile == "fast" and not no_llm:
        console.print("[yellow]Quality profile 'fast' uses heuristic mode for quick runs.[/yellow]")

    # Build LLM provider if needed
    providers: list[ModelProvider] = []
    selected_provider_label = "heuristic"
    if not effective_no_llm:
        if auto:
            providers, selected_provider_label = await _auto_select_provider(
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                verbose=verbose,
            )
            if not providers:
                console.print(
                    "[yellow]Warning:[/yellow] Auto provider detection failed. Falling back to"
                    " heuristic mode."
                )
                effective_no_llm = True
        else:
            try:
                config = load_provider_config(
                    provider=model_provider,
                    model_name=model_name,
                    base_url=base_url,
                    api_key=api_key,
                )
                provider = create_provider(config)
                providers.append(provider)
                selected_provider_label = (
                    f"{provider.name}@{config.resolved_base_url() or 'default'}"
                )

                if verbose:
                    console.print(f"[dim]Using provider: {provider.name}[/dim]")
                    console.print(f"[dim]Endpoint: {config.resolved_base_url() or 'default'}[/dim]")
            except ValueError as exc:
                console.print(f"[yellow]Warning:[/yellow] Could not configure LLM: {exc}")
                console.print("[yellow]Falling back to heuristic mode.[/yellow]")
                effective_no_llm = True

    try:
        # Pre-flight estimate so users can budget expensive runs.
        estimated_modules = await _estimate_module_count(
            project_path,
            exclude_patterns=merged_excludes,
            include_hidden=include_hidden,
        )
        preflight = _estimate_preflight_cost(
            module_count=estimated_modules,
            model_name=providers[0].name if providers else "heuristic",
            use_llm=not effective_no_llm,
            quality_profile=quality_profile,
        )
        console.print(
            Panel.fit(
                f"[bold]Preflight Estimate[/bold]\n"
                f"Modules (estimated): [cyan]{estimated_modules}[/cyan]\n"
                f"LLM summaries (estimated): [cyan]{preflight['llm_operations']}[/cyan]\n"
                f"Tokens (estimated): [cyan]{preflight['total_tokens']:,}[/cyan]\n"
                f"Cost (estimated): [cyan]${preflight['estimated_cost']:.6f}[/cyan]",
                border_style="magenta",
            )
        )

        with create_generation_tracker(console) as tracker:
            # Create generator
            gen_config = GenerationConfig(
                use_llm=not effective_no_llm,
                providers=providers,
                quality_profile=quality_profile,
                include_hidden=include_hidden,
                exclude_patterns=merged_excludes,
                include_mermaid=True,
                template_path=Path(guide_template).resolve() if guide_template else None,
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
        console.print(
            f"[green]✓[/green] Generated guide with {len(result.guide.sections)} sections"
        )
        console.print(f"[green]✓[/green] Analyzed {result.modules_analyzed} modules")
        console.print(f"[green]✓[/green] Generation time: {result.total_time_seconds:.2f}s")
        console.print(f"[green]✓[/green] Quality profile: {quality_profile}")
        console.print(f"[green]✓[/green] LLM summaries: {result.llm_calls_made}")
        console.print(f"[green]✓[/green] Heuristic summaries: {result.heuristic_summaries}")
        console.print(f"[green]✓[/green] Tokens used (estimated): {result.total_tokens_used:,}")
        console.print(f"[green]✓[/green] Cost (estimated): ${result.estimated_cost_usd:.6f}")

        module_llm = max(result.modules_summarized - result.heuristic_summaries, 0)
        module_coverage = (
            (module_llm / result.modules_summarized) * 100 if result.modules_summarized else 0.0
        )
        console.print(
            f"[green]✓[/green] Module LLM coverage: {module_coverage:.1f}%"
            f" ({module_llm}/{result.modules_summarized})"
        )

        if run_report_path:
            _write_run_report(
                report_path=Path(run_report_path),
                project_path=project_path,
                result=result,
                quality_profile=quality_profile,
                provider_label=selected_provider_label,
                auto_mode=auto,
                heuristic_mode=effective_no_llm,
                output_path=Path(output).resolve() if output else None,
            )
            console.print(f"[green]✓[/green] Run report written to: {Path(run_report_path)}")

        if result.errors:
            console.print(f"\n[yellow]Errors ({len(result.errors)}):[/yellow]")
            for error in result.errors[:5]:
                console.print(f"  [yellow]•[/yellow] {error}")
            if len(result.errors) > 5:
                console.print(f"  [dim]... and {len(result.errors) - 5} more[/dim]")

    except DevWayfinderError as exc:
        console.print(f"\n[red]{exc.__class__.__name__}:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"\n[red]ConfigurationError:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        for provider in providers:
            close_method = getattr(provider, "close", None)
            if callable(close_method):
                await close_method()


async def _estimate_module_count(
    project_path: Path,
    *,
    exclude_patterns: list[str] | None = None,
    include_hidden: bool = False,
) -> int:
    """Estimate number of source modules before generation."""
    analyzer = StructureAnalyzer(
        exclude_patterns=exclude_patterns,
        include_hidden=include_hidden,
    )
    info = await analyzer.analyze(project_path)
    return len(info.source_files)


def _estimate_preflight_cost(
    *, module_count: int, model_name: str, use_llm: bool, quality_profile: str
) -> dict[str, int | float]:
    """Estimate token and cost footprint before running generation."""
    if not use_llm or module_count == 0:
        return {
            "llm_operations": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }

    # Adaptive prompting lowers average output size for many utility files.
    avg_input_tokens = 180
    avg_output_tokens = 170
    total_input = module_count * avg_input_tokens
    total_output = module_count * avg_output_tokens

    if quality_profile in {"deep", "balanced"}:
        total_input += 500  # architecture + entry-point synthesis context overhead
        total_output += 350

    total_tokens = total_input + total_output

    estimate = TokenEstimate(
        input_tokens=total_input,
        output_tokens=total_output,
        total_tokens=total_tokens,
    )
    cost = estimate_cost(estimate, model_name=model_name)
    extra_ops = 2 if quality_profile in {"deep", "balanced"} else 0

    return {
        "llm_operations": module_count + extra_ops,
        "total_tokens": total_tokens,
        "estimated_cost": cost.total_cost,
    }


def _normalize_quality_profile(quality: str) -> str:
    """Validate and normalize quality profile names."""
    normalized = quality.strip().lower()
    if normalized not in QUALITY_PROFILES:
        valid = ", ".join(QUALITY_PROFILES)
        raise ValueError(f"Unsupported quality profile '{quality}'. Use: {valid}")
    return normalized


async def _auto_select_provider(
    *,
    model_name: str | None,
    api_key: str | None,
    base_url: str | None,
    verbose: bool,
) -> tuple[list[ModelProvider], str]:
    """Probe likely local endpoints and return the first healthy provider."""
    candidates: list[tuple[str, str]] = []
    if base_url:
        base = base_url.rstrip("/")
        candidates.append(("openai_compat", base))
        if base.endswith("/v1"):
            candidates.append(("ollama", base[: -len("/v1")]))
        else:
            candidates.append(("ollama", base))

    candidates.extend(AUTO_PROVIDER_CANDIDATES)

    unique_candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for provider_name, endpoint in candidates:
        key = (provider_name, endpoint.rstrip("/"))
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append((provider_name, endpoint.rstrip("/")))

    diagnostics: list[str] = []

    for provider_name, endpoint in unique_candidates:
        try:
            config = load_provider_config(
                provider=provider_name,
                model_name=model_name,
                base_url=endpoint,
                api_key=api_key,
                timeout=15,
            )
            provider = create_provider(config)
        except ValueError as exc:
            diagnostics.append(f"{provider_name}@{endpoint}: {exc}")
            continue

        keep_provider = False
        try:
            health = await provider.health_check()
            if health.healthy:
                resolved_endpoint = config.resolved_base_url() or endpoint
                label = f"{provider.name}@{resolved_endpoint}"
                keep_provider = True
                if verbose:
                    console.print(f"[dim]Auto-selected provider: {label}[/dim]")
                return [provider], label

            diagnostics.append(f"{provider.name}@{endpoint}: unhealthy ({health.message})")
        except Exception as exc:
            diagnostics.append(f"{provider_name}@{endpoint}: {exc}")
        finally:
            if not keep_provider:
                close_method = getattr(provider, "close", None)
                if callable(close_method):
                    await close_method()

    if verbose and diagnostics:
        console.print("[dim]Auto provider probe attempts:[/dim]")
        for line in diagnostics[:8]:
            console.print(f"[dim]  - {line}[/dim]")

    return [], "heuristic"


def _write_run_report(
    *,
    report_path: Path,
    project_path: Path,
    result: GenerationResult,
    quality_profile: str,
    provider_label: str,
    auto_mode: bool,
    heuristic_mode: bool,
    output_path: Path | None,
) -> None:
    """Write a concise generation report for guided workflow runs."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    module_llm = max(result.modules_summarized - result.heuristic_summaries, 0)
    module_coverage = (
        (module_llm / result.modules_summarized) * 100 if result.modules_summarized else 0.0
    )

    lines = [
        "# DevWayfinder Run Report",
        "",
        f"- Project: `{project_path}`",
        f"- Quality Profile: `{quality_profile}`",
        f"- Provider: `{provider_label}`",
        f"- Auto Mode: `{auto_mode}`",
        f"- Heuristic Mode: `{heuristic_mode}`",
        f"- Modules Analyzed: `{result.modules_analyzed}`",
        f"- Modules Summarized: `{result.modules_summarized}`",
        f"- Module LLM Coverage: `{module_coverage:.1f}% ({module_llm}/{result.modules_summarized})`",
        f"- LLM Calls: `{result.llm_calls_made}`",
        f"- Heuristic Summaries: `{result.heuristic_summaries}`",
        f"- Tokens Used (estimated): `{result.total_tokens_used}`",
        f"- Cost (estimated): `${result.estimated_cost_usd:.6f}`",
        f"- Generation Time: `{result.total_time_seconds:.2f}s`",
    ]

    if output_path is not None:
        lines.append(f"- Guide Output: `{output_path}`")

    if result.errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for err in result.errors[:8]:
            lines.append(f"- {err}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    project_excludes, include_hidden, config_path = _load_project_analysis_settings(project_path)

    console.print(
        Panel.fit(
            f"[bold blue]DevWayfinder[/bold blue]\nAnalyzing: [cyan]{project_path.name}[/cyan]",
            border_style="blue",
        )
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Structure analysis
            task = progress.add_task("[cyan]Analyzing project structure...", total=None)
            structure_analyzer = StructureAnalyzer(
                exclude_patterns=project_excludes,
                include_hidden=include_hidden,
            )
            structure = await structure_analyzer.analyze(project_path)
            progress.update(task, description="[green]Structure analysis complete!")

            # Build dependency graph
            task2 = progress.add_task("[cyan]Building dependency graph...", total=None)
            graph_builder = GraphBuilder(
                exclude_patterns=project_excludes,
                include_hidden=include_hidden,
            )
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
                if config_path is not None:
                    console.print(f"\n[dim]Using config: {config_path}[/dim]")
                console.print("\n[bold]Core Modules:[/bold]")
                core_modules = graph.get_core_modules(threshold=3)
                for module in core_modules[:10]:
                    deps = len(graph.get_dependencies(module.path))
                    dependents = len(graph.get_dependents(module.path))
                    console.print(
                        f"  [cyan]{module.path.name}[/cyan]: {deps} deps, {dependents} dependents"
                    )

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
    console.print(f"DevWayfinder version {get_version()}")


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


def _merge_patterns(base_patterns: list[str], additional_patterns: list[str]) -> list[str]:
    """Merge two pattern lists while preserving order."""
    merged = list(base_patterns)
    for pattern in additional_patterns:
        if pattern not in merged:
            merged.append(pattern)
    return merged


def _find_project_config_path(project_path: Path) -> Path | None:
    """Find .devwayfinder/config.yaml in current path or ancestors."""
    roots = [project_path]
    roots.extend(project_path.parents)
    for root in roots:
        candidate = root / ".devwayfinder" / "config.yaml"
        if candidate.is_file():
            return candidate
    return None


def _load_project_analysis_settings(project_path: Path) -> tuple[list[str], bool, Path | None]:
    """Load analysis exclude/include settings from local project config when available."""
    config_path = _find_project_config_path(project_path)
    if config_path is None:
        return [], False, None

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        console.print(
            f"[yellow]Warning:[/yellow] Failed to parse {config_path}: {exc}. "
            "Continuing with default analysis settings."
        )
        return [], False, config_path

    if not isinstance(raw, dict):
        return [], False, config_path

    analysis = raw.get("analysis")
    if not isinstance(analysis, dict):
        return [], False, config_path

    loaded_patterns: list[str] = []
    exclude_patterns = analysis.get("exclude_patterns")
    if isinstance(exclude_patterns, list):
        loaded_patterns = [item.strip() for item in exclude_patterns if isinstance(item, str)]

    include_hidden = bool(analysis.get("include_hidden", False))
    return loaded_patterns, include_hidden, config_path
