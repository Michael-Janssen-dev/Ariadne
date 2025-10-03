import click
import sys


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
    from ariadne.storage import ModelStorage
    from pathlib import Path
    from ariadne.use_cases import render_visualization_html
    import webbrowser
    from tempfile import NamedTemporaryFile

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
