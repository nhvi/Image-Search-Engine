from urllib import request
from tensorflow.keras.models import Model
from PIL import Image
import numpy as np
import pandas as pd
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from flask import Flask, request, render_template

def image_preprocess(img):
    img = img.resize((224, 224))
    img = img.convert("RGB")
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis = 0)
    x = preprocess_input(x)
    return x

def extract_vector(model, image_path):
    print("Processing: ", image_path)
    img = Image.open(image_path)
    img_tensor = image_preprocess(img)
    vector = model.predict(img_tensor)[0]
    vector = vector / np.linalg.norm(vector)
    return vector

def get_extract_model():
    vgg16_model = VGG16(weights = "imagenet")
    extract_model = Model(inputs = vgg16_model.inputs, outputs = vgg16_model.get_layer("fc1").output)
    return extract_model

#Read vectors from .csv file
global_df_vectors = pd.read_csv("./static/feature/clusters.csv")

#Read centroids from .csv file
global_centroids = pd.read_csv("./static/feature/centroids.csv")

def evaluate(image_test, content_img_test, global_df_vectors, global_centroids):
    #Initialize model
    model = get_extract_model()
    search_vector = extract_vector(model, image_test)
    #Read vector from .csv file
    df_vectors = global_df_vectors
    #Read centroids from .csv file
    centroids = global_centroids
    #Compare feature of query image and centroid features
    distance = np.linalg.norm(np.array(centroids[centroids.columns[0:4096]]) - search_vector, axis = 1)

    #Select cluster name that have min distance
    min_cluster = list(distance).index(np.min(distance))

    #Select image 
    df_vectors = df_vectors[df_vectors["cluster"] == min_cluster]
    #Ranking cluster
    distance = np.linalg.norm(np.array(df_vectors[df_vectors.columns[0:4096]]) - search_vector, axis = 1)
    df_vectors['distance'] = pd.Series(distance, index = df_vectors.index)
    df_vectors['rank'] = df_vectors['distance'].rank(ascending = 1)
    df_vectors = df_vectors.set_index('rank')
    df_vectors = df_vectors.sort_index()

    df_vect = df_vectors[df_vectors["cluster"] == min_cluster]
    distance = np.linalg.norm(np.array(df_vect[df_vect.columns[0:4096]]) - search_vector, axis = 1)
    df_vect['distance'] = pd.Series(distance, index = df_vect.index)
    df_vect['rank'] = df_vect['distance'].rank(ascending = 1)
    df_vect = df_vect.set_index('rank')
    df_vect = df_vect.sort_index()

    result = df_vectors[0: 100]
    content_compare = []
    for content in result['Content']:
        if str(content) == content_img_test:
            content_compare.append(True)
        else:
            content_compare.append(False)
    result['Content_compare'] = pd.Series(content_compare, index = result.index)
    correct_result = content_compare.count(True)
    precision = correct_result / len(content_compare)
    print('Precision: ', precision)
    return result, precision

#build web Flask
app = Flask(__name__)
@app.route('/', methods = ['GET', 'POST'])

def index():
    if request.method == 'POST':
        file = request.files['query_img']
        #Save the image
        img = Image.open(file) #PIL Image
        uploaded_img_path = "static/uploaded/" + file.filename
        img.save(uploaded_img_path)
        content_image = file.filename[0:3]
        result, ps = evaluate(uploaded_img_path, content_image, global_df_vectors, global_centroids)
        rs = result[['Path', 'Content_compare']]
        rs = rs.to_records(index = False)
        rs = list(rs)
        precision = "Precision: " + str(ps)
        return render_template('index.html', query_path = uploaded_img_path, scores = rs, precision = precision)
    else:
        return render_template('index.html')

if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 8080, debug = True)
