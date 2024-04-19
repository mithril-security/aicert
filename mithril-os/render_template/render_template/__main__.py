import argparse
import yaml
from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined


def render_template(config_path: str, template_path: str):
    # Load variables from the provided YAML file path
    with open(config_path, "r") as config_file:
        variables = yaml.safe_load(config_file)

    # Set up the Jinja2 environment (adjust the template directory path as needed)
    env = Environment(
        loader=FileSystemLoader("."),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # Load the template (adjust the template name as needed)
    template = env.get_template(template_path)

    # Render the template with variables from YAML file
    output = template.render(variables)

    if not template_path.endswith(".j2"):
        raise ValueError(f"File path must end with '.j2', got '{template_path}'")

    with open(template_path[:-3], "wt") as fh:
        fh.write(output)


def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Render a Jinja2 template with variables from a YAML file."
    )
    parser.add_argument(
        "config_path", type=str, help="Path to the YAML file containing variables."
    )
    parser.add_argument(
        "file_path", type=str, help="Path to the Jinja template file."
    )
    args = parser.parse_args()
    render_template(args.config_path, args.file_path)


if __name__ == "__main__":
    main()
