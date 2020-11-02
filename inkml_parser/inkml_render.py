from os.path import join

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas
from skimage.transform import resize
import xml.etree.ElementTree as ET
import os
import numpy as np
from tqdm import tqdm
# import cv2
import pandas as pd


# import split_folders

def get_traces_data(inkml_file_abs_path):
    traces_data = []

    tree = ET.parse(inkml_file_abs_path)
    root = tree.getroot()
    doc_namespace = "{http://www.w3.org/2003/InkML}"

    traceGroupWrapper = root.find(doc_namespace + 'traceGroup')

    'Stores traces_all with their corresponding id'
    traces_all = [{'id': trace_tag.get('{http://www.w3.org/XML/1998/namespace}id'),
                   'coords': [
                       [round(float(axis_coord)) if float(axis_coord).is_integer() else round(float(axis_coord) * 10000) \
                        for axis_coord in coord[1:].split(' ')] if coord.startswith(' ') \
                           else [round(float(axis_coord)) if float(axis_coord).is_integer() else round(
                           float(axis_coord) * 10000) \
                                 for axis_coord in coord.split(' ')] \
                       for coord in (trace_tag.text).replace('\n', '').split(',')]} \
                  for trace_tag in traceGroupWrapper.findall(doc_namespace + 'trace')]

    return traces_all

    # 'Always 1st traceGroup is a redundant wrapper'
    # if traceGroupWrapper is not None:
    #     for traceGroup in traceGroupWrapper.findall(doc_namespace + 'trace'):
    #
    #         # label = traceGroup.find(doc_namespace + 'annotation').text
    #
    #         # 'traces of the current traceGroup'
    #         traces_curr = []
    #         for trace in traceGroup.findall(doc_namespace + 'traceView'):
    #             # 'Id reference to specific trace tag corresponding to currently considered label'
    #             traceDataRef = int(trace.get('xml:id'))
    #
    #             # 'Each trace is represented by a list of coordinates to connect'
    #             single_trace = traces_all[traceDataRef]['coords']
    #             traces_curr.append(single_trace)
    #
    #         traces_data.append({'label': label, 'trace_group': traces_curr})
    #
    # else:
    #     'Consider Validation data that has no labels'
    #     [traces_data.append({'trace_group': [trace['coords']]}) for trace in traces_all]
    #
    # return traces_data


def inkml2img(input_path, output_path):
    #     print(input_path)
    #     print(pwd)
    traces = get_traces_data(input_path)

    i = 0
    plt.gca().invert_yaxis()
    plt.gca().set_aspect('equal', adjustable='box')
    plt.axes().get_xaxis().set_visible(False)
    plt.axes().get_yaxis().set_visible(False)
    plt.axes().spines['top'].set_visible(False)
    plt.axes().spines['right'].set_visible(False)
    plt.axes().spines['bottom'].set_visible(False)
    plt.axes().spines['left'].set_visible(False)
    for elem in traces:
        i += 1
        label = elem['id']
        ls = elem['coords']

        df = pandas.DataFrame(ls)

        x = df[0]
        y = df[1]

        plt.plot(x, y, "-o", ms=1, marker='.', c='black')

        if i >= 20:
            print(i)
            break
        else:
            print(i)
        plt.savefig(join(output_path, label + ".png"), bbox_inches='tight', dpi=400)

    plt.gcf().clear()

# for file in tqdm(files):
#     #     print(file)
#     inkml2img(path + '/CROHME_training_2011/' + file, '/kaggle/Image_data/finaltrain/')
#
