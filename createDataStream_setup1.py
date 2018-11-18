#!/usr/bin/python

import re
import sys
import time
import numpy
from utils import readConfig, readIndices, getCoNNL_label2int, getMatrixForContext, adaptNumSamplesTrain, getRelID, getNerID, cleanContext, reverse
import theano
import pickle


if len(sys.argv) != 2:
  print "please pass the config file as parameters"
  exit(0)

time1 = time.time()

configfile = sys.argv[1]
config = readConfig(configfile)

datafile = config["datafile"]

if "wordvectors" in config:
  wordvectorfile = config["wordvectors"]
  print "wordvector file ", wordvectorfile
  wordindices = readIndices(wordvectorfile, isWord2vec = True)
else:
  print "you have to either specify a wordvector file"
  exit()
contextsize = 120 # maximum sentence length is 118
print "contextsize ", contextsize
entitysize = int(config["entitysize"])
filename = config["file"]
print "filename for storing data ", filename

label2int = getCoNNL_label2int()

time1 = time.time()

# read pickled file
data_in = open(datafile, 'rb')
train_id2sent = pickle.load(data_in)
train_id2pos = pickle.load(data_in)
train_id2ner = pickle.load(data_in)
train_id2nerBILOU = pickle.load(data_in)
train_id2arg2rel = pickle.load(data_in)

test_id2sent = pickle.load(data_in)
test_id2pos = pickle.load(data_in)
test_id2ner = pickle.load(data_in)
test_id2nerBILOU = pickle.load(data_in)
test_id2arg2rel = pickle.load(data_in)
data_in.close()

def splitContext(context, curId, id2ner, id2arg2rel):
  contextList = context.split()
  curNers = id2ner[curId].split()
  entities = []
  x1List = []
  x2List = []
  x3List = []
  x4List = []
  e1List = []
  e2List = []
  yList = []
  yE1List = []
  yE2List = []
  e1IdList = []
  e2IdList = []
  i = 0
  while i < len(curNers):
    j = i + 1
    while j < len(curNers) and curNers[i] == curNers[j]:
      j += 1
    if curNers[i] != "O":
      entities.append((i, j-1))
    i = j
  for e1Ind in range(len(entities)):
    for e2Ind in range(e1Ind+1, len(entities)):
      # entity pair (e1, e2)
      ent1 = entities[e1Ind]
      ent2 = entities[e2Ind]
      x1 = contextList[:ent1[0]]
      e1 = contextList[ent1[0]:ent1[1]+1]
      x2 = contextList[ent1[1]+1:]
      x3 = contextList[:ent2[0]]
      e2 = contextList[ent2[0]:ent2[1]+1]
      x4 = contextList[ent2[1]+1:]
      y = 0
      if (ent1[1],ent2[1]) in id2arg2rel[curId]:
        y = getRelID(id2arg2rel[curId][(ent1[1],ent2[1])])
      yE1 = getNerID(curNers[ent1[1]])
      yE2 = getNerID(curNers[ent2[1]])
      x1List.append(x1)
      x2List.append(x2)
      x3List.append(x3)
      x4List.append(x4)
      e1List.append(e1)
      e2List.append(e2)
      yList.append(y)
      yE1List.append(yE1)
      yE2List.append(yE2)
      e1IdList.append(e1Ind)
      e2IdList.append(e2Ind)

      # entity pair (e2, e1):
      x1 = contextList[:ent2[0]]
      e1 = contextList[ent2[0]:ent2[1]+1]
      x2 = contextList[ent2[1]+1:]
      x3 = contextList[:ent1[0]]
      e2 = contextList[ent1[0]:ent1[1]+1]
      x4 = contextList[ent1[1]+1:]
      y = 0
      if (ent2[1],ent1[1]) in id2arg2rel[curId]:
        y = getRelID(id2arg2rel[curId][(ent2[1],ent1[1])])
      yE1 = getNerID(curNers[ent2[1]])
      yE2 = getNerID(curNers[ent1[1]])
      x1List.append(x1)
      x2List.append(x2)
      x3List.append(x3)
      x4List.append(x4)
      e1List.append(e1)
      e2List.append(e2)
      yList.append(y)
      yE1List.append(yE1)
      yE2List.append(yE2)
      e1IdList.append(e2Ind)
      e2IdList.append(e1Ind)
  return x1List, x2List, x3List, x4List, e1List, e2List, yList, yE1List, yE2List, e1IdList, e2IdList

def processSamples(id2sent, id2ner, id2arg2rel, wordindices):
  x1List = []
  x2List = []
  x3List = []
  x4List = []
  e1List = []
  e2List = []
  yList = []
  yE1List = []
  yE2List = []
  idList = []
  e1IdList = []
  e2IdList = []
  
  for curId in id2sent:
    context = id2sent[curId]
    curX1, curX2, curX3, curX4, curE1, curE2, curYrel, curY1et, curY2et, curE1Id, curE2Id = splitContext(context, curId, id2ner, id2arg2rel)

    for ex in range(len(curX1)):
      curX1[ex] = cleanContext(curX1[ex])
      curX2[ex] = cleanContext(curX2[ex])
      curX3[ex] = cleanContext(curX3[ex])
      curX4[ex] = cleanContext(curX4[ex])

      matrixX1 = getMatrixForContext(curX1[ex], contextsize, wordindices)
      matrixX1 = numpy.reshape(matrixX1, contextsize)
      matrixX2 = getMatrixForContext(curX2[ex], contextsize, wordindices)
      matrixX2 = numpy.reshape(matrixX2, contextsize)
      matrixX3 = getMatrixForContext(curX3[ex], contextsize, wordindices)
      matrixX3 = numpy.reshape(matrixX3, contextsize)
      matrixX4 = getMatrixForContext(curX4[ex], contextsize, wordindices)
      matrixX4 = numpy.reshape(matrixX4, contextsize)

      matrixE1 = getMatrixForContext(curE1[ex], entitysize, wordindices)
      matrixE1 = numpy.reshape(matrixE1, entitysize)
      matrixE2 = getMatrixForContext(curE2[ex], entitysize, wordindices)
      matrixE2 = numpy.reshape(matrixE2, entitysize)   

      x1List.append(matrixX1)
      x2List.append(matrixX2)
      x3List.append(matrixX3)
      x4List.append(matrixX4)
      e1List.append(matrixE1)
      e2List.append(matrixE2)
      yList.append(curYrel[ex])
      yE1List.append(curY1et[ex])
      yE2List.append(curY2et[ex])
      idList.append(curId)
      e1IdList.append(curE1Id[ex])
      e2IdList.append(curE2Id[ex])
  
  x1_numpy = numpy.array(x1List)
  x2_numpy = numpy.array(x2List)
  x3_numpy = numpy.array(x3List)
  x4_numpy = numpy.array(x4List)
  e1_numpy = numpy.array(e1List)
  e2_numpy = numpy.array(e2List)
  y_numpy = numpy.array(yList)
  yE1_numpy = numpy.array(yE1List)
  yE2_numpy = numpy.array(yE2List)
  id_numpy = numpy.array(idList)
  e1Id_numpy = numpy.array(e1IdList)
  e2Id_numpy = numpy.array(e2IdList)
  
  return x1_numpy, x2_numpy, x3_numpy, x4_numpy, e1_numpy, e2_numpy, y_numpy, yE1_numpy, yE2_numpy, id_numpy, e1Id_numpy, e2Id_numpy


x1Train, x2Train, x3Train, x4Train, e1Train, e2Train, yTrain, yE1Train, yE2Train, idTrain, e1IdTrain, e2IdTrain = processSamples(train_id2sent, train_id2ner, train_id2arg2rel, wordindices)
numSamples = x1Train.shape[0]

x1Test, x2Test, x3Test, x4Test, e1Test, e2Test, yTest, yE1Test, yE2Test, idTest, e1IdTest, e2IdTest = processSamples(test_id2sent, test_id2ner, test_id2arg2rel, wordindices)
numSamplesTest = x1Test.shape[0]

time2 = time.time()
print "time for reading data: " + str(time2 - time1)

dt = theano.config.floatX

# split train into train and dev
numSamplesTrain = int(0.8 * numSamples)
# don't split same sentence id into train and dev
numSamplesTrain = adaptNumSamplesTrain(numSamplesTrain, idTrain)
print "samples for training: ", numSamplesTrain
numSamplesDev = numSamples - numSamplesTrain
print "samples for development: ", numSamplesDev
numSamplesTotal = numSamplesTrain + numSamplesDev + numSamplesTest

x1Dev = x1Train[numSamplesTrain:]
x1Train = x1Train[:numSamplesTrain]
x2Dev = x2Train[numSamplesTrain:]
x2Train = x2Train[:numSamplesTrain]
x3Dev = x3Train[numSamplesTrain:]
x3Train = x3Train[:numSamplesTrain]
x4Dev = x4Train[numSamplesTrain:]
x4Train = x4Train[:numSamplesTrain]
yDev = yTrain[numSamplesTrain:]
yTrain = yTrain[:numSamplesTrain]
yE1Dev = yE1Train[numSamplesTrain:]
yE1Train = yE1Train[:numSamplesTrain]
yE2Dev = yE2Train[numSamplesTrain:]
yE2Train = yE2Train[:numSamplesTrain]
e1Dev = e1Train[numSamplesTrain:]
e1Train = e1Train[:numSamplesTrain]
e2Dev = e2Train[numSamplesTrain:]
e2Train = e2Train[:numSamplesTrain]
idDev = idTrain[numSamplesTrain:]
idTrain = idTrain[:numSamplesTrain]
e1IdDev = e1IdTrain[numSamplesTrain:]
e1IdTrain = e1IdTrain[:numSamplesTrain]
e2IdDev = e2IdTrain[numSamplesTrain:]
e2IdTrain = e2IdTrain[:numSamplesTrain]


################ FUEL #################
import h5py
from fuel.datasets.hdf5 import H5PYDataset

f = h5py.File(filename, mode='w')

feat_x1 = f.create_dataset('x1', (numSamplesTotal, contextsize), dtype = numpy.dtype(numpy.int32), compression='gzip')
feat_x2 = f.create_dataset('x2', (numSamplesTotal, contextsize), dtype = numpy.dtype(numpy.int32), compression='gzip')
feat_x3 = f.create_dataset('x3', (numSamplesTotal, contextsize), dtype = numpy.dtype(numpy.int32), compression='gzip')
feat_x4 = f.create_dataset('x4', (numSamplesTotal, contextsize), dtype = numpy.dtype(numpy.int32), compression='gzip')
feat_e1 = f.create_dataset('e1', (numSamplesTotal, entitysize), dtype=numpy.dtype(numpy.int32), compression='gzip')
feat_e2 = f.create_dataset('e2', (numSamplesTotal, entitysize), dtype=numpy.dtype(numpy.int32), compression='gzip')
label_y = f.create_dataset('y', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')
label_y1ET = f.create_dataset('y1ET', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')
label_y2ET = f.create_dataset('y2ET', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')
sent_id = f.create_dataset('sent_id', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')
e1_id = f.create_dataset('e1_id', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')
e2_id = f.create_dataset('e2_id', (numSamplesTotal, 1), dtype=numpy.dtype(numpy.int32), compression='gzip')

feat_x1[...] = numpy.vstack([x1Train, x1Dev, x1Test]).reshape(numSamplesTotal, contextsize)
feat_x2[...] = numpy.vstack([x2Train, x2Dev, x2Test]).reshape(numSamplesTotal, contextsize)
feat_x3[...] = numpy.vstack([x3Train, x3Dev, x3Test]).reshape(numSamplesTotal, contextsize)
feat_x4[...] = numpy.vstack([x4Train, x4Dev, x4Test]).reshape(numSamplesTotal, contextsize)
feat_e1[...] = numpy.vstack([e1Train, e1Dev, e1Test]).reshape(numSamplesTotal, entitysize)
feat_e2[...] = numpy.vstack([e2Train, e2Dev, e2Test]).reshape(numSamplesTotal, entitysize)
label_y[...] = numpy.vstack([yTrain.reshape(numSamplesTrain, 1), yDev.reshape(numSamplesDev, 1), yTest.reshape(numSamplesTest, 1)]) #.reshape(numSamplesTotal, 1)
label_y1ET[...] = numpy.vstack([yE1Train.reshape(numSamplesTrain, 1), yE1Dev.reshape(numSamplesDev, 1), yE1Test.reshape(numSamplesTest, 1)]) #.reshape((numSamplesTotal, 1))
label_y2ET[...] = numpy.vstack([yE2Train.reshape(numSamplesTrain, 1), yE2Dev.reshape(numSamplesDev, 1), yE2Test.reshape(numSamplesTest, 1)]) #.reshape((numSamplesTotal, 1))
sent_id[...] = numpy.vstack([idTrain.reshape(numSamplesTrain, 1), idDev.reshape(numSamplesDev, 1), idTest.reshape(numSamplesTest, 1)]) #.reshape((numSamplesTotal, 1))
e1_id[...] = numpy.vstack([e1IdTrain.reshape(numSamplesTrain, 1), e1IdDev.reshape(numSamplesDev, 1), e1IdTest.reshape(numSamplesTest, 1)])
e2_id[...] = numpy.vstack([e2IdTrain.reshape(numSamplesTrain, 1), e2IdDev.reshape(numSamplesDev, 1), e2IdTest.reshape(numSamplesTest, 1)])

start_train = 0
end_train = start_train + numSamplesTrain
start_dev = end_train
end_dev = start_dev + numSamplesDev
start_test = end_dev
end_test = start_test + numSamplesTest

split_dict = {'train' :
               {'x1':(start_train,end_train), 'x2':(start_train,end_train), 
                'x3':(start_train,end_train), 'x4':(start_train,end_train), 
                'e1':(start_train,end_train), 'e2':(start_train,end_train),
                'y':(start_train,end_train), 'y1ET': (start_train,end_train), 
                'y2ET':(start_train,end_train), 'sent_id':(start_train,end_train), 
                'e1_id':(start_train,end_train), 'e2_id':(start_train,end_train)},
             'dev' :
               {'x1':(start_dev,end_dev), 'x2':(start_dev,end_dev), 
                'x3':(start_dev,end_dev), 'x4':(start_dev,end_dev), 
                'e1':(start_dev,end_dev), 'e2': (start_dev,end_dev),
                'y':(start_dev,end_dev), 'y1ET':(start_dev,end_dev), 
                'y2ET': (start_dev,end_dev), 'sent_id':(start_dev,end_dev), 
                'e1_id':(start_dev,end_dev), 'e2_id':(start_dev,end_dev)},
             'test' :
               {'x1':(start_test,end_test), 'x2':(start_test,end_test), 
                'x3':(start_test,end_test), 'x4':(start_test,end_test), 
                'e1':(start_test,end_test), 'e2': (start_test,end_test),
                'y':(start_test,end_test), 'y1ET':(start_test,end_test), 
                'y2ET': (start_test,end_test), 'sent_id':(start_test,end_test), 
                'e1_id':(start_test,end_test), 'e2_id':(start_test,end_test)}}

f.attrs['split'] = H5PYDataset.create_split_array(split_dict)

f.flush()
f.close()
