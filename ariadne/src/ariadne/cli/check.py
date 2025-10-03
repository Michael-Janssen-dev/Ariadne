import click
import sys
from pathlib import Path


def list_checkers(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from ariadne.use_cases import list_conformance_checkers

    checkers = list_conformance_checkers()
    click.echo("Available Conformance Checkers:")
    for checker in checkers:
        click.echo(f"- {checker}")
    ctx.exit()


@click.command("check")
@click.option(
    "-f",
    "--file",
    help="Path to the trace data file (CSV format). If not provided, reads from stdin.",
    type=click.File("rt"),
    default=sys.stdin,
)
@click.option(
    "--model-dir",
    "-m",
    help="Path to the directory containing stored models.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
)
@click.option(
    "--checker",
    "-c",
    help="Conformance checking algorithm to use.",
    required=True,
)
@click.option(
    "--list-checkers",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=list_checkers,
    help="List all available conformance checking plugins and exit.",
)
@click.pass_context
def check_conformance(ctx, file, model_dir, algorithm):
    """Check conformance of models against trace data"""
    from ariadne.use_cases import check_conformance
    from ariadne.storage import ModelStorage
    import pandas as pd

    try:
        df = pd.read_csv(file)
        model_storage = ModelStorage(Path(model_dir))
        results = check_conformance(df, algorithm, model_storage=model_storage)
        click.echo(f"Conformance results: {results}", err=True)
    except Exception as e:
        if ctx.obj.verbose:
            import traceback

            traceback.print_exc()
        raise click.ClickException(f"Error during conformance checking: {e}")
