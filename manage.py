from flask.cli import FlaskGroup
from app import app, db  # pastikan import app dan db dari tempat yang sesuai

cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
