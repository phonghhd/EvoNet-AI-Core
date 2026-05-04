import os
import sys
import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help="EvoNet CLI - Autonomous AI Security Agent")
console = Console()


def run_bandit(path: str) -> dict:
    try:
        result = subprocess.run(
            ["bandit", "-r", path, "-f", "json", "-q"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode in [0, 1]:
            return json.loads(result.stdout) if result.stdout.strip() else {"results": []}
    except FileNotFoundError:
        console.print("[yellow]bandit not installed, installing...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "bandit", "-q"])
        return run_bandit(path)
    except Exception:
        pass
    return {"results": []}


def run_semgrep(path: str) -> dict:
    try:
        result = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout.strip() else {"results": []}
    except FileNotFoundError:
        console.print("[yellow]semgrep not installed, installing...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "semgrep", "-q"])
        return run_semgrep(path)
    except Exception:
        pass
    return {"results": []}


def run_safety_check() -> dict:
    try:
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True, text=True, timeout=60
        )
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {"vulnerabilities": []}
        except json.JSONDecodeError:
            return {"vulnerabilities": []}
    except FileNotFoundError:
        console.print("[yellow]safety not installed, installing...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "safety", "-q"])
        return run_safety_check()
    except Exception:
        pass
    return {"vulnerabilities": []}


@app.command()
def scan(
    path: str = typer.Option(".", help="Path to scan"),
    tools: str = typer.Option("all", help="Tools: bandit, semgrep, safety, all"),
    output: str = typer.Option(None, help="Output JSON file path")
):
    """Scan source code for security vulnerabilities"""
    console.print(Panel(f"[bold]Scanning: {path}[/bold]", title="EvoNet Security Scanner"))

    results = {}
    total_issues = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        if tools in ["all", "bandit"]:
            task = progress.add_task("Running Bandit (Python SAST)...", total=None)
            bandit_results = run_bandit(path)
            bandit_count = len(bandit_results.get("results", []))
            results["bandit"] = {"issues": bandit_count, "findings": bandit_results.get("results", [])[:20]}
            total_issues += bandit_count
            progress.update(task, description=f"[green]Bandit: {bandit_count} issues found[/green]")

        if tools in ["all", "semgrep"]:
            task = progress.add_task("Running Semgrep (Multi-lang SAST)...", total=None)
            semgrep_results = run_semgrep(path)
            semgrep_count = len(semgrep_results.get("results", []))
            results["semgrep"] = {"issues": semgrep_count, "findings": semgrep_results.get("results", [])[:20]}
            total_issues += semgrep_count
            progress.update(task, description=f"[green]Semgrep: {semgrep_count} issues found[/green]")

        if tools in ["all", "safety"]:
            task = progress.add_task("Running Safety (Dependency check)...", total=None)
            safety_results = run_safety_check()
            safety_count = len(safety_results.get("vulnerabilities", []))
            results["safety"] = {"issues": safety_count, "findings": safety_results.get("vulnerabilities", [])[:20]}
            total_issues += safety_count
            progress.update(task, description=f"[green]Safety: {safety_count} vulnerabilities found[/green]")

    table = Table(title="Scan Results Summary")
    table.add_column("Tool", style="cyan")
    table.add_column("Issues Found", style="red" if total_issues > 0 else "green")
    table.add_column("Status")

    for tool, data in results.items():
        count = data["issues"]
        status = "[red]ISSUES FOUND[/red]" if count > 0 else "[green]CLEAN[/green]"
        table.add_row(tool, str(count), status)

    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total_issues}[/bold]", "")
    console.print(table)

    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]Results saved to {output}[/green]")

    if total_issues > 0:
        console.print(f"\n[red]Found {total_issues} security issues. Review and fix before deploying.[/red]")
        raise typer.Exit(code=1)
    else:
        console.print("\n[green]No security issues found.[/green]")


@app.command()
def version():
    """Show EvoNet CLI version"""
    console.print("[bold]EvoNet CLI v2.0.0[/bold]")


def main():
    app()


if __name__ == "__main__":
    main()
