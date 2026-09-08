import os
from pathlib import Path

import typer

app = typer.Typer(help="Runtrail — Agent Run-Trace-Evaluate Harness")


@app.callback()
def _main() -> None:
    """Keep `ui` (and future subcommands) addressable as `runtrail <command>`
    instead of Typer collapsing a single command into the top-level app.
    """


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: str = "runtrail.db",
) -> None:
    """Start the optional Web UI.

    Set the RUNTRAIL_STORE_DSN environment variable to back it with
    PostgresStore instead of the default SQLiteStore (e.g. from
    docker-compose.yml) — requires the 'postgres' extra.
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(
            "The Runtrail Web UI requires the 'ui' extra: pip install 'runtrail[ui]'"
        ) from exc

    from runtrail.storage.base import BaseStore
    from runtrail.ui.main import create_app

    dsn = os.environ.get("RUNTRAIL_STORE_DSN")
    store: BaseStore
    if dsn:
        from runtrail.storage.postgres_store import PostgresStore

        store = PostgresStore(dsn)
    else:
        from runtrail.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(db_path)

    web_app = create_app(store=store)
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def report(path: str) -> None:
    """Print a CLI summary of a JSON report produced by Report.to_json()."""
    from runtrail.observability.reporter import Report

    report_obj = Report.from_json(Path(path))
    stats = report_obj.stats()

    typer.echo(report_obj.summary())
    typer.echo(
        f"avg duration: {stats['avg_duration_ms']:.1f}ms   "
        f"avg steps: {stats['avg_steps']:.1f}   "
        f"total tokens: {stats['total_tokens']}"
    )
    if stats["failure_category_counts"]:
        typer.echo("failure categories:")
        for category, count in sorted(stats["failure_category_counts"].items(), key=lambda kv: -kv[1]):
            typer.echo(f"  {category}: {count}")


@app.command()
def regress(
    suite_name: str,
    report_path: str,
    save_baseline: bool = False,
    baseline_dir: str = ".runtrail_baselines",
) -> None:
    """Check a Report.to_json() file against a named RegressionSuite baseline.

    Exits non-zero if a regression is found — wire this into CI to gate on
    Agent regressions the same way you'd gate on failing unit tests. Pass
    --save-baseline to record `report_path` as the new baseline instead of
    checking against it.
    """
    from runtrail.observability.reporter import Report
    from runtrail.runtime.regression import RegressionSuite

    suite = RegressionSuite(suite_name, baseline_dir=baseline_dir)
    report_obj = Report.from_json(Path(report_path))

    if save_baseline:
        suite.save_baseline(report_obj)
        typer.echo(f"saved baseline for '{suite_name}' ({report_obj.summary()})")
        return

    if not suite.has_baseline():
        typer.echo(f"no baseline for '{suite_name}' yet — run with --save-baseline first")
        raise typer.Exit(code=1)

    result = suite.check(report_obj)
    typer.echo(result.summary())
    if result.regressed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
