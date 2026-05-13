import click

from ariadne._go import collect


@click.command("collect")
def collect_traces():
    collect("60s")
