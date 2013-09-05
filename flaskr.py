# -*- coding: utf-8 -*-
"""
Flaskr
~~~~~~

A tiny library management system
with Flask and sqlite3.

:copyright: (c) 2013 by Jonas Bru.
"""

from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
import urllib
import hashlib
from qrcode import *
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, _app_ctx_stack
from reportlab.graphics.barcode import code39, code128, code93
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
import cStringIO
from flask import make_response

# configuration
DATABASE = "flaskr.db"
DEBUG = True
SECRET_KEY = "development key"
USERNAME = "admin"
PASSWORD = "default"

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar("FLASKR_SETTINGS", silent=True)


def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql") as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, "sqlite_db"):
        sqlite_db = sqlite3.connect(app.config["DATABASE"])
        sqlite_db.row_factory = sqlite3.Row
        top.sqlite_db = sqlite_db

    return top.sqlite_db


@app.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, "sqlite_db"):
        top.sqlite_db.close()


@app.route("/")
def show_entries():
    db = get_db()
    cur = db.execute("select * from books order by title asc")
    books = cur.fetchall()

    borrowedBooks = None
    if session.get("logged_in"):
        borrowedBooks = db.execute("select * from books where borrower=? order by title asc", [session["username"]]).fetchall()

    return render_template("show_books.html", books=books, borrowedBooks=borrowedBooks)


@app.route("/add", methods=["GET"])
def add_book():
    if not session.get("logged_in"):
        abort(401)
    return render_template("modify_book.html", book={}, action="add")


@app.route("/addG", methods=["GET"])
def add_book_G():
    if not session.get("logged_in"):
        abort(401)
    return render_template("add_google.html", book={}, action="add")


@app.route("/add", methods=["POST"])
def add_book_post():
    if not session.get("logged_in"):
        abort(401)
    if request.form.get("title") is None or request.form.get("title") == "":
        return render_template("modify_book.html", action="add", book={}, error="Empty title")

    db = get_db()
    db.execute(
        "insert into books (title, description, authors, publisher, publisherDate, ISBN, thumbnail, webReaderLink)"
        " values (?, ?, ?, ?, ?, ?, ?, ?)",
        [request.form["title"], request.form["description"], request.form["authors"], request.form["publisher"],
         request.form["publisherDate"], request.form["ISBN"], request.form["thumbnail"], request.form["webReaderLink"]])

    idB = db.execute("select last_insert_rowid()").fetchone()

    db.commit()

    flash(request.form.get("title") + " was successfully added")

    return redirect(url_for("detail", post_id=int(idB[0])))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == "":
            error = "Empty username"
        else:
            session.permanent = True
            session["logged_in"] = True
            session["username"] = request.form["username"]
            session["mail"] = request.form["mail"]

            if session["mail"] == "":
                url = session["username"]
            else:
                url = session["mail"]

            gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(url.lower()).hexdigest() + "?"
            gravatar_url += urllib.urlencode({'d': "wavatar"})
            session["gravatar"] = gravatar_url

            flash("Hi " + session["username"] + "!")
            return redirect(url_for("show_entries"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("You were logged out")
    return redirect(url_for("show_entries"))


@app.route("/detail/<int:post_id>")
def detail(post_id, error=""):
    db = get_db()
    cur = db.execute("select * from books where id=?", str(post_id))
    book = cur.fetchone()
    return render_template("detail_book.html", book=book, error=error)


@app.route("/modify/<int:post_id>", methods=["GET"])
def modify(post_id):
    if not session.get("logged_in"):
        abort(401)
    db = get_db()
    cur = db.execute("select * from books where id=?", str(post_id))
    book = cur.fetchone()
    return render_template("modify_book.html", book=book, action="modify")


@app.route("/modify/<int:post_id>", methods=["POST"])
def modify_post(post_id):
    if not session.get("logged_in"):
        abort(401)
    db = get_db()
    db.execute("update books set title=?, description=?, authors=?, publisher=?, "
               "ISBN=?, thumbnail=?, webReaderLink=? where id=?",
               [request.form["title"], request.form["description"], request.form["authors"], request.form["publisher"],
                request.form["ISBN"], request.form["thumbnail"], request.form["webReaderLink"], post_id])
    db.commit()
    flash("The book " + request.form["title"] + " was successfully updated!")
    return redirect(url_for("detail", post_id=post_id))


@app.route("/borrow/<int:post_id>", methods=["POST"])
def borrow_post(post_id):
    if not session.get("logged_in"):
        abort(401)

    db = get_db()
    cur = db.execute("select borrower from books where id=?", [post_id])
    bor = cur.fetchone()

    if not (bor[0] is None or bor[0] == ""):
        book = db.execute("select * from books where id=?", str(post_id)).fetchone()
        return render_template("detail_book.html", book=book, error="Book already borrowed!")

    db.execute("update books set borrower=?, borrowerGr=? where id=?", [session["username"], session["gravatar"], post_id])
    db.execute("insert into borrowings (borrower, borrowerGr, date, action) values (?, ?, date('now'), \"borrow\")", [session["username"], session["gravatar"]])

    db.commit()

    flash("The book " + request.form["title"] + " was successfully borrowed!")

    return redirect(url_for("show_entries"))


@app.route("/return/<int:post_id>", methods=["POST"])
def return_post(post_id):
    if not session.get("logged_in"):
        abort(401)

    db = get_db()
    cur = db.execute("select borrower from books where id=?", [post_id])
    bor = cur.fetchone()

    print(bor)

    # if bor[0] is None or bor[0] == "" or bor[0] != session.get("username"):
    #     book = db.execute("select * from books where id=?", str(post_id)).fetchone()
    #     return render_template("detail_book.html", book=book, error="It's not you that borrowed that book!")

    db.execute("update books set borrower=?, borrowerGr=? where id=?", ["", "", post_id])
    db.execute("insert into borrowings (borrower, borrowerGr, date, action) values (?, ?, date('now'), \"return\")", [session["username"], session["gravatar"]])

    db.commit()

    flash("The book " + request.form["title"] + " was successfully returned!")

    return redirect(url_for("show_entries"))



@app.route("/qr/<int:post_id>", methods=["GET"])
@app.route("/QR/<int:post_id>", methods=["GET"])
def QR_get(post_id):
    db = get_db()
    cur = db.execute("select * from books where id=?", str(post_id))
    book = cur.fetchone()

    return render_template("qr_book.html", book=book)

@app.route("/qrM/<title>", methods=["GET"])
@app.route("/QRM/<title>", methods=["GET"])
def QR_get_title(title):
    db = get_db()
    cur = db.execute("select * from books where title=?", [title])
    book = cur.fetchone()

    return render_template("qr_book.html", book=book)


@app.route("/QR", methods=["GET"])
def QR_generate():
    db = get_db()
    cur = db.execute("select * from books order by title asc")
    books = cur.fetchall()

    return render_template("generate_qr.html", books=books)

@app.route("/QR_gen", methods=["POST"])
def QR():
    print request.form
    # qr = QRCode(version=20, error_correction=ERROR_CORRECT_L)
    # qr.add_data("http://blog.matael.org/")
    # qr.make() # Generate the QRCode itself
    #
    # # im contains a PIL.Image.Image object
    # im = qr.make_image()
    #
    # # To save it
    # im.save("./filename.png")
    #
    # img = make("http://127.0.0.1:5000/detail/1")
    # img.save("/home/jbrumonserrat/workspace/flaskr/plop.png")

    # c = canvas.Canvas("barcodes.pdf", pagesize=letter)
    #
    # # draw a QR code
    # qr_code = qr.QrCodeWidget('www.mousevspython.com')
    # bounds = qr_code.getBounds()
    # width = bounds[2] - bounds[0]
    # height = bounds[3] - bounds[1]
    # taille = 100.
    # d = Drawing(taille, taille, transform=[taille/width,0,0,taille/height,0,0])
    # d.add(qr_code)
    #
    # for x in xrange(0,3):
    #     for y in xrange(0,6):
    #         renderPDF.draw(d, c, 35 + x*200, 45 + y*120)
    #         c.drawString(35 + x*200, 35 + y*120,"Welcome to Reportlab!")
    #
    # c.save()
    #
    # return redirect(url_for("show_entries"))

    output = cStringIO.StringIO()

    c = canvas.Canvas(output)
    # c = canvas.Canvas("barcodes.pdf", pagesize=letter)

    # draw a QR code

    x = 0
    y = 0
    for bookId in request.form:
        print bookId
        db = get_db()
        cur = db.execute("select * from books where id=?", [bookId])
        book = cur.fetchone()

        url = url_for('QR_get_title', title=book[1], _external=True)

        qr_code = qr.QrCodeWidget(url)
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        size = 100.
        d = Drawing(size, size, transform=[size / width, 0, 0, size / height, 0, 0])
        d.add(qr_code)
        renderPDF.draw(d, c, 35 + x * 200, 45 + y * 120)
        c.drawString(35 + x * 200, 35 + y * 120, book[1])

        x = (x + 1) % 3
        if x == 0 :
            y = (y + 1) % 6

    # for y in xrange(0,6):
    #     for x in xrange(0,3):
    #         db = get_db()
    #         cur = db.execute("select * from books where id=?", [title])
    #         book = cur.fetchone()
    #
    #         qr_code = qr.QrCodeWidget('www.mousevspython.com')
    #         bounds = qr_code.getBounds()
    #         width = bounds[2] - bounds[0]
    #         height = bounds[3] - bounds[1]
    #         taille = 100.
    #         d = Drawing(taille, taille, transform=[taille/width,0,0,taille/height,0,0])
    #         d.add(qr_code)
    #         renderPDF.draw(d, c, 35 + x*200, 45 + y*120)
    #         c.drawString(35 + x*200, 35 + y*120,"Welcome to Reportlab!")

    c.save()
    pdf_out = output.getvalue()
    output.close()

    response = make_response(pdf_out)
    response.headers['Content-Disposition'] = "attachment; filename='books_to_print.pdf"
    response.mimetype = 'application/pdf'

    return response

if __name__ == "__main__":
    init_db()
    app.run()