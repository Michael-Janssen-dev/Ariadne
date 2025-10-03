from ariadne.cli.convert.elastic import from_elastic
import click


@click.group()
def convert():
    """Convert to OTEL CSV format from other formats"""
    pass


convert.add_command(from_elastic)
