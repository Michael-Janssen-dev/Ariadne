import csv
import os
import sys
from pathlib import Path

import click

from ariadne._go import collect
from ariadne.use_cases import list_conformance_checkers, list_miners


@click.group()
def cli():
    """Ariadne CLI: Process Mining for Microservice Traces"""


def _list_plugins_callback(ls, label):
    def callback(ctx, param, value):
        if value or ctx.resilient_parsing:
            return value
        click.echo("Error: Missing option '--algorithm' / '-a'", err=True)
        click.echo(f"Available {label} algorithms:", err=True)
        for name, display_name, license in ls:
            click.echo(f"- {name}({license}): {display_name}", err=True)
        ctx.exit()

    return callback


def algorithm(name: str, list_fn):
    options = list_fn()
    return click.option(
        "--algorithm",
        "--algo",
        "-a",
        help=f"{name.capitalize()} algorithm to use.",
        is_eager=True,
        callback=_list_plugins_callback(options, name),
        type=click.Choice([x[0] for x in options]),
    )


@cli.command()
@algorithm("miner", list_miners)
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
def mine(file, output_dir, algorithm):
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
    process_trace_data(df, algorithm, storage=storage)
    click.echo(f"Models saved to directory: {output_dir}", err=True)


@cli.command("check")
@algorithm("checker", list_conformance_checkers)
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
@click.pass_context
def check_conformance(ctx, file, model_dir, algorithm):
    """Check conformance of models against trace data"""
    import pandas as pd

    from ariadne.storage import ModelStorage
    from ariadne.use_cases import check_conformance

    df = pd.read_csv(file)
    model_storage = ModelStorage(Path(model_dir))
    results = check_conformance(df, algorithm, model_storage=model_storage)

    with open("results.csv", "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "service_name",
                "operation_name",
                "fitness",
                "precision",
                "simplicity",
                "generalization",
            ]
        )
        for name, r in results.items():
            writer.writerow(
                [
                    name[0],
                    name[1],
                    r.fitness,
                    r.precision,
                    r.simplicity,
                    r.generalization,
                ]
            )


@cli.group("import")
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


convert.add_command(from_elastic)


@cli.command()
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
def inspect(model_dir, output_path):
    """Inspect process models"""
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
        f"HTML saved to {output_path if output_path != sys.stdout else 'stdout'}",
        err=True,
    )


@cli.command("collect")
@click.option(
    "--duration",
    help="Specify how long traces will be collected",
    default="60s",
    type=str,
)
def collect_traces(duration):
    """Collect traces from an OpenTelemetry Collector"""
    collect(duration)


if __name__ == "__main__":
    cli()
