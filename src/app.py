import os
import secrets
import tempfile
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

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
    dict_to_flashcards,
    flashcards_to_dict,
    generate_flashcards,
)
from src.ocr import extract_text_from_pdf, _get_max_pages
from src.anki import get_anki_service

load_dotenv()


def _get_secret_key() -> str:
    key = os.getenv("FLASK_SECRET_KEY")
    if key:
        return key
    return secrets.token_hex(32)


def _get_flask_host() -> str:
    return os.getenv("FLASK_HOST", "0.0.0.0")


def _get_flask_port() -> int:
    return int(os.getenv("FLASK_PORT", "5000"))


app = Flask(__name__)
app.secret_key = _get_secret_key()

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

ALLOWED_EXTENSIONS = {"pdf"}

progress_store = {}
flashcard_store = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    session_id = session.get("_id", "")
    if not session_id:
        session_id = secrets.token_hex(8)
        session["_id"] = session_id
        session.modified = True
    flashcards = flashcard_store.get(session_id, [])
    processing = session.get("processing", False)
    pdf_filename = session.get("pdf_filename", "")
    return render_template(
        "index.html",
        flashcards=flashcards,
        processing=processing,
        pdf_filename=pdf_filename,
        session_id=session_id,
    )


@app.route("/config", methods=["GET"])
def get_config():
    return jsonify(
        {
            "host": _get_flask_host(),
            "port": _get_flask_port(),
            "max_pages": _get_max_pages(),
        }
    )


def process_pdf_background(session_id, temp_path, max_pages):
    def ocr_progress(current, total):
        progress_store[session_id] = {
            "stage": "ocr",
            "current": current,
            "total": total,
            "percent": int((current / total) * 100) if total > 0 else 0,
        }

    def flashcard_progress(current, total):
        progress_store[session_id] = {
            "stage": "flashcards",
            "current": current,
            "total": total,
            "percent": int((current / total) * 100) if total > 0 else 0,
        }

    try:
        pages = extract_text_from_pdf(
            temp_path, max_pages, progress_callback=ocr_progress
        )

        total_pages = len(pages)
        for i in range(total_pages):
            flashcard_progress(i + 1, total_pages)

        flashcards = generate_flashcards(pages)

        progress_store[session_id] = {
            "stage": "complete",
            "current": total_pages,
            "total": total_pages,
            "percent": 100,
            "flashcards": flashcards_to_dict(flashcards),
        }
    except Exception as e:
        progress_store[session_id] = {
            "stage": "error",
            "error": str(e),
        }


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

    session_id = session.get("_id", secrets.token_hex(8))
    session["_id"] = session_id
    session["processing"] = True
    session["pdf_filename"] = file.filename
    flashcard_store[session_id] = []
    session.modified = True

    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(temp_path)

    max_pages = session.get("max_pages")

    progress_store[session_id] = {
        "stage": "starting",
        "current": 0,
        "total": 0,
        "percent": 0,
    }

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(process_pdf_background, session_id, temp_path, max_pages)

    return redirect("/")


@app.route("/progress", methods=["GET"])
def get_progress():
    session_id = session.get("_id")
    if not session_id or session_id not in progress_store:
        return jsonify({"stage": "idle"})

    progress = progress_store[session_id].copy()

    if progress.get("stage") == "complete":
        flashcards = progress.get("flashcards", [])
        flashcard_store[session_id] = flashcards
        session["processing"] = False
        session.modified = True
        flash(f"Generated {len(flashcards)} flashcards", "success")
        del progress_store[session_id]

    return jsonify(progress)


@app.route("/cards", methods=["GET"])
def get_cards():
    session_id = session.get("_id", "")
    return jsonify(flashcard_store.get(session_id, []))


@app.route("/config/max_pages", methods=["POST"])
def set_max_pages():
    data = request.json
    max_pages = data.get("max_pages")
    if max_pages is not None:
        try:
            max_pages = int(max_pages) if max_pages != "" else None
        except ValueError:
            return jsonify({"error": "max_pages must be a number"}), 400
    session["max_pages"] = max_pages
    return jsonify({"success": True, "max_pages": max_pages})


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
        anki = get_anki_service()
        decks = anki.get_decks()
        return jsonify({"decks": decks})
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

    try:
        anki = get_anki_service()
        count = anki.add_notes(deck_name, flashcards)
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        debug=True, host=_get_flask_host(), port=_get_flask_port(), use_reloader=False
    )
