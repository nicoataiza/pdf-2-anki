import os
import secrets
import tempfile

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
)

from src.flashcards import (
    Flashcard,
    dict_to_flashcards,
    flashcards_to_dict,
    generate_flashcards,
)
from src.ocr import extract_text_from_pdf

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    flashcards = session.get("flashcards", [])
    processing = session.get("processing", False)
    pdf_filename = session.get("pdf_filename", "")
    return render_template(
        "index.html",
        flashcards=flashcards,
        processing=processing,
        pdf_filename=pdf_filename,
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file part", "error")
        return redirect("/")

    file = request.files["file"]
    if file.filename == "":
        flash("No selected file", "error")
        return redirect("/")

    if not allowed_file(file.filename):
        flash("Only PDF files are allowed", "error")
        return redirect("/")

    session["processing"] = True
    session["pdf_filename"] = file.filename
    session["flashcards"] = []
    session.modified = True

    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(temp_path)

    try:
        pages = extract_text_from_pdf(temp_path)
        flashcards = generate_flashcards(pages)
        session["flashcards"] = flashcards_to_dict(flashcards)
        flash(f"Generated {len(flashcards)} flashcards", "success")
    except Exception as e:
        flash(f"Error processing PDF: {str(e)}", "error")
    finally:
        os.remove(temp_path)
        session["processing"] = False
        session.modified = True

    return redirect("/")


@app.route("/cards", methods=["GET"])
def get_cards():
    return jsonify(session.get("flashcards", []))


@app.route("/export/csv", methods=["POST"])
def export_csv():
    selected = request.json.get("cards", [])
    if not selected:
        flash("No cards selected", "error")
        return redirect("/")

    flashcards = dict_to_flashcards(selected)

    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    try:
        import csv

        writer = csv.writer(temp_file, delimiter="\t")
        writer.writerow(["front", "back"])
        for card in flashcards:
            writer.writerow([card.front, card.back])

        temp_file.close()
        return send_file(
            temp_file.name,
            mimetype="text/csv",
            as_attachment=True,
            download_name="flashcards.csv",
        )
    except Exception as e:
        flash(f"Error exporting: {str(e)}", "error")
        return redirect("/")


@app.route("/anki/decks", methods=["GET"])
def get_decks():
    try:
        import requests

        response = requests.post(
            "http://localhost:8765",
            json={"action": "deckNames", "version": 6},
            timeout=5,
        )
        data = response.json()
        if data.get("error"):
            return jsonify({"error": data["error"]}), 400
        return jsonify({"decks": data.get("result", [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/anki/add", methods=["POST"])
def add_to_anki():
    data = request.json
    cards = data.get("cards", [])
    deck_name = data.get("deck", "").strip()

    if not cards:
        return jsonify({"error": "No cards selected"}), 400

    if not deck_name:
        return jsonify({"error": "Deck name is required"}), 400

    flashcards = dict_to_flashcards(cards)

    notes = []
    for card in flashcards:
        notes.append(
            {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {"Front": card.front, "Back": card.back},
                "options": {"allowDuplicate": False},
                "tags": card.tags,
            }
        )

    try:
        import requests

        response = requests.post(
            "http://localhost:8765",
            json={"action": "addNotes", "version": 6, "params": {"notes": notes}},
            timeout=30,
        )
        result = response.json()

        if result.get("error"):
            return jsonify({"error": result["error"]}), 400

        count = len(result.get("result", []))
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
