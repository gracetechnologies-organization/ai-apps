import logging
from logging.handlers import RotatingFileHandler
from  flask import Flask, jsonify
from blueprints.version_blueprint import vchecker_blurprint
from blueprints.word2pdf import docx2pdf_blueprint
from blueprints.pdf2word import pdf2word_blueprint
from blueprints.pptx2pdf import ppt2pdf_blueprint
from blueprints.pdf2ppt import pdf2ppt_blueprint
from blueprints.xlsx2pdf import xls2pdf_blueprint
from blueprints.pdf2xls import pdf2xls_blueprint
from blueprints.iosresume_blueprint import iosresume_blueprint
from blueprints.andresume_blueprint import andresume_blueprint
from blueprints.coverletter_blueprint import letter_blueprint
from blueprints.webresume_blueprint import webresume_blueprint
from blueprints.SR_blueprint import SR_blueprint
from blueprints.Denoiser_blurprint import Denoising_blueprint
from blueprints.PortraitEnhancer_blueprint import PE_blueprint
from blueprints.rembg_blueprint import bgrem_blueprint


app = Flask(__name__)

log_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] - %(message)s'
)
log_handler = RotatingFileHandler('app.log', maxBytes= 1024 * 1024, backupCount=5)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(log_formatter)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

app.register_blueprint(vchecker_blurprint)
app.register_blueprint(docx2pdf_blueprint)
app.register_blueprint(pdf2word_blueprint)
app.register_blueprint(ppt2pdf_blueprint)
app.register_blueprint(pdf2ppt_blueprint)
app.register_blueprint(xls2pdf_blueprint)
app.register_blueprint(pdf2xls_blueprint)
app.register_blueprint(iosresume_blueprint)
app.register_blueprint(andresume_blueprint)
app.register_blueprint(letter_blueprint)
app.register_blueprint(webresume_blueprint)
app.register_blueprint(SR_blueprint)
app.register_blueprint(Denoising_blueprint)
app.register_blueprint(PE_blueprint)
app.register_blueprint(bgrem_blueprint)

if __name__  == '__main__':
    app.run(debug=True, host= "0.0.0.0")