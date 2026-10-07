from django.core.management.commands import makemessages


class Command(makemessages.Command):
    """makemessages without fuzzy matching: a new message must be translated by hand, never
    get a similar-looking old translation guessed by msgmerge."""

    msgmerge_options = [*makemessages.Command.msgmerge_options, "--no-fuzzy-matching"]
