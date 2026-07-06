"""`nav db migrate` — apply pending schema migrations and report."""

import click


@click.command("migrate")
@click.pass_context
def db_migrate(ctx):
    """Apply any pending schema migrations to the database.

    Migrations also run automatically whenever navtool opens the database, so
    this is mainly an explicit, transparent way to trigger and report them.
    """
    # The top-level group already migrated the database on connect; report what
    # that did on this run.
    from_version, to_version = ctx.obj["migration"]
    if from_version == to_version:
        click.echo(f"Database already up to date (schema version {to_version}).")
    else:
        click.echo(
            f"Migrated database from schema version {from_version} to {to_version}."
        )
