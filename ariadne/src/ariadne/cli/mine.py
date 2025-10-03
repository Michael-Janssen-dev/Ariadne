import click
import os
import sys


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
    import pandas as pd
    from ariadne.use_cases import process_trace_data
    from ariadne.storage import ModelStorage
    from pathlib import Path

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
