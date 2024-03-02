from flask import Flask, jsonify, Blueprint

vchecker_blurprint = Blueprint("versionchecker", __name__)

@vchecker_blurprint.route("/versioncheck")
def Version_Checker():
    return jsonify ({"Version" : "Version 1.0.4 containing Pdf Converters, Stable Diffusion, IOS Resume (Bedrock) and Android (ChatGPT) without Threadings, and Cover Letter Apps"})
    