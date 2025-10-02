import click


@click.group()
def cli():
    """Ariadne CLI: Process Mining for Microservice Traces"""
    pass


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
