# -*- coding: utf-8 -*-
import os
import sys
import glob
import tarfile
import pickle
import subprocess
import numpy as np
from sklearn.preprocessing import OneHotEncoder

EPOCHS = 10
BATCHSIZE = 64
LR = 0.01
MOMENTUM = 0.9
N_CLASSES = 10
GPU = True

if sys.version_info.major == 2:
    # Backward compatibility with python 2.
    from six.moves import urllib
    urlretrieve = urllib.request.urlretrieve
else:
    from urllib.request import urlretrieve

def get_gpu_name():
    try:
        out_str = subprocess.run(["nvidia-smi", "--query-gpu=gpu_name", "--format=csv"], stdout=subprocess.PIPE).stdout
        out_list = out_str.decode("utf-8").split('\n')
        out_list = out_list[1:-1]
        return out_list
    except Exception as e:
        print(e)


def get_cuda_version():
    """Get CUDA version"""
    if sys.platform == 'win32':
        raise NotImplementedError("Implement this!")
        # This breaks on linux:
        #cuda=!ls "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
        #path = "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\" + str(cuda[0]) +"\\version.txt"
    elif sys.platform == 'linux' or sys.platform == 'darwin':
        path = '/usr/local/cuda/version.txt'
    else:
        raise ValueError("Not in Windows, Linux or Mac")
    if os.path.isfile(path):
        with open(path, 'r') as f:
            data = f.read().replace('\n','')
        return data
    else:
        return "No CUDA in this machine"

def get_cudnn_version():
    """Get CUDNN version"""
    if sys.platform == 'win32':
        raise NotImplementedError("Implement this!")
        # This breaks on linux:
        #cuda=!ls "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
        #candidates = ["C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\" + str(cuda[0]) +"\\include\\cudnn.h"]
    elif sys.platform == 'linux':
        candidates = ['/usr/include/x86_64-linux-gnu/cudnn_v[0-99].h',
                      '/usr/local/cuda/include/cudnn.h',
                      '/usr/include/cudnn.h']
    elif sys.platform == 'darwin':
        candidates = ['/usr/local/cuda/include/cudnn.h',
                      '/usr/include/cudnn.h']
    else:
        raise ValueError("Not in Windows, Linux or Mac")
    for c in candidates:
        file = glob.glob(c)
        if file: break
    if file:
        with open(file[0], 'r') as f:
            version = ''
            for line in f:
                if "#define CUDNN_MAJOR" in line:
                    version = line.split()[-1]
                if "#define CUDNN_MINOR" in line:
                    version += '.' + line.split()[-1]
                if "#define CUDNN_PATCHLEVEL" in line:
                    version += '.' + line.split()[-1]
        if version:
            return version
        else:
            return "Cannot find CUDNN version"
    else:
        return "No CUDNN in this machine"



def read_batch(src):
    '''Unpack the pickle files
    '''
    with open(src, 'rb') as f:
        if sys.version_info.major == 2:
            data = pickle.load(f)
        else:
            data = pickle.load(f, encoding='latin1')
    return data


def shuffle_data(X, y):
    s = np.arange(len(X))
    np.random.shuffle(s)
    X = X[s]
    y = y[s]
    return X, y


def yield_mb(X, y, batchsize=64, shuffle=False):
    if shuffle:
        X, y = shuffle_data(X, y)
    # Only complete batches are submitted
    for i in range(len(X) // batchsize):
        yield X[i * batchsize:(i + 1) * batchsize], y[i * batchsize:(i + 1) * batchsize]

def process_cifar():
    '''Load data into RAM'''
    print('Preparing train set...')
    train_list = [read_batch('./cifar-10-batches-py/data_batch_{0}'.format(i + 1)) for i in range(5)]
    x_train = np.concatenate([t['data'] for t in train_list])
    y_train = np.concatenate([t['labels'] for t in train_list])
    print('Preparing test set...')
    tst = read_batch('./cifar-10-batches-py/test_batch')
    x_test = tst['data']
    y_test = np.asarray(tst['labels'])
    return x_train, x_test, y_train, y_test

def maybe_download_cifar(src="https://ikpublictutorial.blob.core.windows.net/deeplearningframeworks/cifar-10-python.tar.gz"):
    '''Load the training and testing data
    Mirror of: http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
    '''
    try:
        return process_cifar()
    except:
        # Catch the exception that file doesn't exist
        # Download
        print('Data does not exist. Downloading ' + src)
        fname, h = urlretrieve(src, './delete.me')
        print('Extracting files...')
        with tarfile.open(fname) as tar:
            tar.extractall()
        os.remove(fname)
        return process_cifar()


def cifar_for_library(channel_first=True, one_hot=False):
    # Raw data
    x_train, x_test, y_train, y_test = maybe_download_cifar()
    # Scale pixel intensity
    x_train = x_train / 255.0
    x_test = x_test / 255.0
    # Reshape
    x_train = x_train.reshape(-1, 3, 32, 32)
    x_test = x_test.reshape(-1, 3, 32, 32)
    # Channel last
    if not channel_first:
        x_train = np.swapaxes(x_train, 1, 3)
        x_test = np.swapaxes(x_test, 1, 3)
    # One-hot encode y
    if one_hot:
        y_train = np.expand_dims(y_train, axis=-1)
        y_test = np.expand_dims(y_test, axis=-1)
        enc = OneHotEncoder(categorical_features='all')
        fit = enc.fit(y_train)
        y_train = fit.transform(y_train).toarray()
        y_test = fit.transform(y_test).toarray()
    # dtypes
    x_train = x_train.astype(np.float32)
    x_test = x_test.astype(np.float32)
    y_train = y_train.astype(np.int32)
    y_test = y_test.astype(np.int32)
    return x_train, x_test, y_train, y_test

import torchvision
import torchvision.transforms as transforms
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data as data_utils
import torch.nn.init as init
from torch.autograd import Variable

print("OS: ", sys.platform)
print("Python: ", sys.version)
print("PyTorch: ", torch.__version__)
print("Numpy: ", np.__version__)
print("GPU: ", get_gpu_name())
print(get_cuda_version())
print("CuDNN Version ", get_cudnn_version())

x_train, x_test, y_train, y_test = cifar_for_library(channel_first = True)
print(x_train.shape, x_test.shape, y_train.shape, y_test.shape)
print(x_train.dtype, x_test.dtype, y_train.dtype, y_test.dtype)

class create_pytorch_model(nn.Module):
    def __init__(self, n_classes=N_CLASSES):
        super(create_pytorch_model, self).__init__()
        self.conv1 = nn.Conv2d(3, 50, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(50, 50, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(50, 100, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(100, 100, kernel_size=3, padding=1)
        # feature map size is 8*8 by pooling
        self.fc1 = nn.Linear(100*8*8, 512)
        self.fc2 = nn.Linear(512, n_classes)

    def forward(self, x):
        # PyTorch requires a flag for training in dropout
        x = self.conv2(F.relu(self.conv1(x)))
        x = F.relu(F.max_pool2d(x, kernel_size=2, stride=2))
        x = F.dropout(x, 0.25, training=self.training)

        x = self.conv4(F.relu(self.conv3(x)))
        x = F.relu(F.max_pool2d(x, kernel_size=2, stride=2))
        x = F.dropout(x, 0.25, training=self.training)

        x = x.view(-1, 100*8*8)   # reshape Variable
        x = F.dropout(F.relu(self.fc1(x)), 0.5, training=self.training)
        return self.fc2(x)

model = create_pytorch_model().cuda()

optimizer = optim.SGD(model.parameters(), LR, MOMENTUM)
criterion = nn.CrossEntropyLoss()

model.train()
for j in range(EPOCHS):
    for data, target in yield_mb(x_train, y_train, BATCHSIZE, shuffle=True):
        data = Variable(torch.FloatTensor(data).cuda())
        target = Variable(torch.LongTensor(target).cuda())
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
    print('Epoch %d' % (j))

model.eval() # Sets training = False
n_samples = (y_test.shape[0]//BATCHSIZE)*BATCHSIZE
y_guess = np.zeros(n_samples, dtype=np.int)
y_truth = y_test[:n_samples]
c = 0
for data, target in yield_mb(x_test, y_test, BATCHSIZE):
    output = model(Variable(torch.FloatTensor(data).cuda()))
    pred = output.data.max(1)[1].cpu().numpy().squeeze()
    y_guess[c*BATCHSIZE:(c+1)*BATCHSIZE] = pred
    c += 1

print("Accuracy: ", 1.*sum(y_guess == y_truth)/len(y_guess))
