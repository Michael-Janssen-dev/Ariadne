from ariadne.cli.convert import convert
from ariadne.cli.mine import mine
from ariadne.cli.check import check_conformance
from ariadne.cli.visualize import visualize
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


cli.add_command(mine)
cli.add_command(check_conformance)
cli.add_command(convert)
cli.add_command(visualize)

if __name__ == "__main__":
    cli()
