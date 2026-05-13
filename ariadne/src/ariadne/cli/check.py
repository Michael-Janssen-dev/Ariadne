import sys
from pathlib import Path

import click

from ariadne.use_cases import list_conformance_checkers


def list_checkers(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from ariadne.use_cases import list_conformance_checkers

    checkers = list_conformance_checkers()
    click.echo("Available Conformance Checkers:")
    for checker in checkers:
        click.echo(f"- {checker}")
    ctx.exit()


AVAILABLE_CHECKERS = [x[0] for x in list_conformance_checkers()]


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
    type=click.Choice(AVAILABLE_CHECKERS),
)
@click.pass_context
def check_conformance(ctx, file, model_dir, checker):
    """Check conformance of models against trace data"""
    import pandas as pd

    from ariadne.storage import ModelStorage
    from ariadne.use_cases import check_conformance

    # try:
    df = pd.read_csv(file)
    model_storage = ModelStorage(Path(model_dir))
    results = check_conformance(df, checker, model_storage=model_storage)
    click.echo(f"Conformance results: {results}", err=True)
    # except Exception as e:
    #     if ctx.obj.verbose:
    #         import traceback

    #         traceback.print_exc()
    #     raise click.ClickException(f"Error during conformance checking: {e}")
