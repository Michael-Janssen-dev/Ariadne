import os
from pathlib import Path
import sys
from ariadne.storage import ModelStorage
import click


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


@cli.command()
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
    help="Mining algorithm to use (see 'list-miners' command).",
    required=True,
)
def mine(file, output_dir, miner):
    import pandas as pd
    from ariadne.use_cases import process_trace_data

    if os.isatty(file.fileno()):
        raise click.ClickException("No input file provided or stdin is not a terminal.")
    click.echo(
        f"Processing file: {file.name if file != sys.stdin else 'stdin'}", err=True
    )

    storage = ModelStorage(Path(output_dir))
    df = pd.read_csv(file)
    try:
        process_trace_data(df, miner, storage=storage)
    except Exception as e:
        raise click.ClickException(f"Error during processing: {e}")
    click.echo(f"Models saved to directory: {output_dir}", err=True)


@cli.command("check")
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
    "--algorithm",
    "-a",
    help="Conformance checking algorithm to use (see 'list-conformance-checkers' command).",
    required=True,
)
@click.pass_context
def check_conformance(ctx, file, model_dir, algorithm):
    """Check conformance of models against trace data"""
    from ariadne.use_cases import check_conformance
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


@cli.group()
def convert():
    """Convert to OTEL CSV format from other formats"""
    pass


@convert.command()
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


@cli.command()
def list_miners():
    """List all available mining plugins"""
    from ariadne.infrastructure.plugin_registry import mining_registry

    plugins = mining_registry.list_plugins()

    click.echo("Available Mining Plugins:")
    for plugin_name in plugins:
        click.echo(f"- {plugin_name}")


if __name__ == "__main__":
    cli()
