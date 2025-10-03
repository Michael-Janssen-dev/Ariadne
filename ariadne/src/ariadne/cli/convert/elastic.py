import click
import sys


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
