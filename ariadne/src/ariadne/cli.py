import os
import sys
from pathlib import Path

import click
import pandas as pd

from ariadne._go import collect
from ariadne.use_cases import list_conformance_checkers


class CLIContext:
    def __init__(self):
        self.verbose = False


@click.group()
@click.option(
    "--verbose", "-v", is_flag=True, help="Enable verbose output for debugging"
)
@click.pass_context
def cli(ctx, verbose):
    """Ariadne CLI: Process Mining for Microservice Traces"""
    context = CLIContext()
    context.verbose = verbose
    ctx.obj = context


def list_miners(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from ariadne.use_cases import list_miners

    miners = list_miners()
    click.echo("Available Mining Plugins:")
    for miner in miners:
        click.echo(f"- {miner}")
    ctx.exit()


@click.command()
@click.option(
    "-f",
    "--file",
    help="Path to the trace data file (CSV format). If not provided, reads from stdin.",
    type=click.File("rt"),
    default=sys.stdin,
)
@click.option(
    "--output-dir",
    "-o",
    help="Path to the output directory. If not provided, writes to stdout.",
    type=click.Path(writable=True, file_okay=False, dir_okay=True),
    required=True,
)
@click.option(
    "--miner",
    help="Mining algorithm to use.",
    required=True,
)
@click.option(
    "--list-miners",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=list_miners,
)
def mine(file, output_dir, miner):
    from pathlib import Path

    import pandas as pd

    from ariadne.storage import ModelStorage
    from ariadne.use_cases import process_trace_data

    if os.isatty(file.fileno()):
        raise click.ClickException("No input file provided or stdin is not a terminal.")
    click.echo(
        f"Processing file: {file.name if file != sys.stdin else 'stdin'}", err=True
    )

    storage = ModelStorage(Path(output_dir))
    df = pd.read_csv(file)
    # try:
    process_trace_data(df, miner, storage=storage)
    # except Exception as e:
    #     raise click.ClickException(f"Error during processing: {e}")
    click.echo(f"Models saved to directory: {output_dir}", err=True)


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


@click.group()
def convert():
    """Convert to OTEL CSV format from other formats"""
    pass


@click.command()
@click.option(
    "-f",
    "--file",
    help="Path to the trace data file (CSV format). If not provided, reads from stdin.",
    type=click.File("rt"),
    default=sys.stdin,
)
@click.option(
    "--output-path",
    "-o",
    help="Path to the output file. If not provided, writes to stdout.",
    type=click.File("wt"),
    default=sys.stdout,
)
def from_elastic(file, output_path):
    """Convert Elastic APM CSV export to OTEL-compatible CSV.

    This command reads a CSV file exported from Elastic APM and
    transforms it into a format compatible with the OTEL Process Mining Tool.
    """
    import pandas as pd

    from ariadne.use_cases import convert_elastic_csv_to_otel

    try:
        df = pd.read_csv(file)
        output = convert_elastic_csv_to_otel(df)
        output.to_csv(output_path, index=False, lineterminator="\n")
        click.echo(
            f"Converted OTEL CSV saved to {output_path if output_path != sys.stdout else 'stdout'}",
            err=True,
        )

    except Exception as e:
        raise click.ClickException(f"Error during conversion: {e}")


convert.add_command(from_elastic)


@click.command()
@click.option(
    "--model-dir",
    "-m",
    help="Path to the directory containing stored models.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
)
@click.option(
    "--output-path",
    "-o",
    help="Path to the output HTML file. If not provided, writes to stdout.",
    type=click.File("wt"),
    default=sys.stdout,
)
@click.option(
    "--open",
    is_flag=True,
    help="Open the generated HTML file in the default web browser after creation.",
)
def visualize(model_dir, output_path, open):
    """Visualize process models and traces"""
    import webbrowser
    from pathlib import Path
    from tempfile import NamedTemporaryFile

    from ariadne.storage import ModelStorage
    from ariadne.use_cases import render_visualization_html

    storage = ModelStorage(Path(model_dir))

    html_content = render_visualization_html(storage)

    if output_path == sys.stdout and open:
        output_path = NamedTemporaryFile(delete=False, suffix=".html", mode="w")
    output_path.write(html_content)
    click.echo(
        f"Visualization HTML saved to {output_path if output_path != sys.stdout else 'stdout'}",
        err=True,
    )
    if open:
        webbrowser.open_new_tab(f"file://{Path(output_path.name).resolve()}")


@click.command("collect")
def collect_traces():
    collect("60s")


if __name__ == "__main__":
    cli()
