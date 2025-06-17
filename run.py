from app import create_app, db

app = create_app()

@app.before_request
def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    app.run(debug=True)