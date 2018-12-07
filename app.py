################################################################## App Utilities
import os
from flask_bootstrap import Bootstrap
from flask import Flask, Response, render_template, current_app, request, redirect, url_for, flash
from flask_restful import Api, Resource
from flask_uploads import UploadSet, configure_uploads, IMAGES

from skimage.io import imread
from skimage.transform import resize

import requests
import subprocess
import json

import numpy as np
import keras
import h5py
from keras.models import load_model   
import tensorflow as tf



################################################################### APP SETTINGS ##############################################################


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") 
Bootstrap(app)
api = Api(app)

photos = UploadSet('photos', IMAGES)                                            ## image upload handling
app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'
configure_uploads(app, photos)
ALLOWED_EXTENSIONS = set(['jpg'])  ## For cat vs dog classifier only


## DEFINE ALLOWED TEMPLATE FILE FORMAT ##############################################   
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS    



###################################################################### RESOURCES ##############################################################


class ImageRecognition(Resource):
    def post(self):
        
        ## Get the Image URL
        url = request.form['url']
        try:
            r = requests.get(url)
        except requests.exceptions.RequestException as e:
            return Response(render_template('404.html'))
        
        
        retJson = {}
        folder_path = os.getcwd() + '/classify_image/'
        file_path = os.getcwd() + '/classify_image/text.txt'
        image_path = os.getcwd() + '/static/guess_image/temp.jpg'
        warning = ''
        
        ## Pass image to the TF model
        with open(image_path, 'wb') as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir={} --image_file={}'.format(folder_path, image_path), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            ret = proc.communicate()[0]
            proc.wait()
        with open(file_path) as f:
            retJson = json.load(f)
            
        ### Get Percentage Value    
        retJson.update((x, y*100) for x, y in retJson.items())
 
        if not retJson:
            warning = "File path not recognized"

        
        
        return Response(render_template('classify.html', retJson=retJson, url = url, warning = warning, mimetype='text/html'))
        
        
class CatDogClassify(Resource):
    def post(self):
        
        model_path = os.getcwd() + '/cat_dog_classifier/image_classifier.h5'
        warning = ""
        if 'photo' in request.files:
            img = request.files['photo']  
            if allowed_file(img.filename):
                keras.backend.clear_session()                                           ## clear Tensor session to avoid error
                image_classifier = load_model(model_path)                               ## load saved model
                class_labels = {0:'Cat', 1:'Dog'}                                       ## prepare labels
                img = imread(request.files['photo'])                                    ## read photo & transform it into array
                img = resize(img,(128,128))
                img = np.expand_dims(img,axis=0)
                if(np.max(img)>1):
                    img = img/255.0
                prediction = image_classifier.predict_classes(img)                      ## predict class    
                guess = class_labels[prediction[0][0]]                                  ## for website display
                keras.backend.clear_session()                                           ## clear Tensor session to avoid error
                
                return Response(render_template('cat_dog_classify.html', guess=guess, mimetype='text/html'))
                
            else:
                return Response(render_template('cat_dog_classifier.html', warning = "Wrong Image Format"))    

     


api.add_resource(ImageRecognition, '/classify')
api.add_resource(CatDogClassify, '/catdogclassify')








########################################################################## VIEWS ######################################################################



############################################################## Home

@app.route('/')
@app.route('/dashboard')
def dashboard():
    
    return render_template("dashboard.html")
    

@app.route('/classify_image')    
def classify_image():
    
    return render_template("classify_image.html")
    
    
@app.route('/cat_dog_classifier')
def cat_dog_classifier():
    
    return render_template("cat_dog_classifier.html")
    
    
    
    
    
    
@app.errorhandler(404)
def error404(error):
    return render_template('404.html'), 404
    
@app.errorhandler(500)
def error500(error):
    return render_template('500.html'), 500    
    
    
    
    
################################################################# APP INITIATION #############################################################


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)     