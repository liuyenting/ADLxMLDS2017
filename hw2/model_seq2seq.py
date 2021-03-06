from video import Video

import os
# set TensorFlow log level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# set Keras backend
os.environ['KERAS_BACKEND'] = 'tensorflow'

from keras.models import model_from_json

import argparse
from os import rename
from os.path import exists, getmtime
from datetime import datetime as dt

import logging
logger = logging.getLogger()

# set the logging format
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname).1s %(asctime)s] %(message)s',
                              '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# set the global log level
logger.setLevel(logging.DEBUG)

import keras
from keras.models import Model
from keras.layers import Input, LSTM, Dense

def build(**kwargs):
    # number of features per frame
    n_features = kwargs['n_features']
    # number of words in the dictionary, one hot
    n_words = kwargs['n_words']
    # Timesteps
    n_timesteps = kwargs['n_timesteps']
    # number of hidden dimensions
    latent_dim = kwargs['latent_dim']

    enc_in = Input(shape=(n_timesteps, n_features))
    enc_lstm = LSTM(latent_dim, return_state=True)
    enc_out, state_h, state_c = enc_lstm(enc_in)

    states = [state_h, state_c]

    # additional dimension for the tags
    dec_in = Input(shape=(n_timesteps, n_words))
    dec_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
    dec_dense = Dense(n_words, activation='softmax')

    dec_out, _, _ = dec_lstm(dec_in, initial_state=states)
    dec_out = dec_dense(dec_out)

    # create the model
    model = Model([enc_in, dec_in], dec_out)
    print(model.summary())

    return model

def train(model, dataset, batch_size=16, epochs=1, validation_split=0.2):
    #model.fit(dataset.x, dataset.y, validation_split=validation_split,
    #          batch_size=batch_size, epcohs=epochs)
    n_samples = len(dataset)
    logger.info('{} samples to train on'.format(n_samples))
    model.fit_generator(dataset.generator(),
                        steps_per_epoch=n_samples, epochs=epochs)

def compile(model):
    model.compile(optimizer='adam', loss='categorical_crossentropy')

def evaluate(model, dataset):
    model.evaluate_generator(dataset.generator(), len(dataset))

def load(name, strict=False):
    """
    Load the latest model.

    Parameters
    ----------
    name: str
        name of the model file
    strict: bool, default to False
        set to True if the model must exists
    """
    model_file = '{}.json'.format(name)
    weight_file = '{}.h5'.format(name)
    if not exists(model_file) or not exists(weight_file):
        if strict:
            raise IOError('Model file not found')
        else:
            return None
    else:
        # load the model
        with open(model_file, 'r') as fd:
            model = model_from_json(fd.read())
        # load weights
        model.load_weights(weight_file)

        logger.info('Model \'{}\' loaded'.format(name))
        return model

def save(model, name):
    """
    Save the model to file.

    Parameters
    ----------
    model: Keras Sequence
        The actual model object.
    name: str
        Name of the model to save.
    """
    # serialize model
    model_file = '{}.json'.format(name)
    with open(model_file, 'w') as fd:
        fd.write(model.to_json())
    # serialize weights
    weight_file = '{}.h5'.format(name)
    model.save_weights(weight_file)

    logger.info('Model saved as \'{}\''.format(name))

def archive(name):
    """
    Archive the specified model to avoid overwrite. Last-access timestamps is
    supplied as suffix for archive name.

    Parameters
    ----------
    name: str
        Name of the model file, without file extensions.
    """
    model_file = '{}.json'.format(name)
    weight_file = '{}.h5'.format(name)
    for f in [model_file, weight_file]:
        if exists(f):
            timestamp = dt.fromtimestamp(getmtime(f)).strftime('%Y%m%d-%H%M%S')
            rename(f, '{}_{}.json'.format(name, timestamp))
    logger.info('Archived last active model')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Video captioning using a sequence-to-sequence model.')
    parser.add_argument('folder', type=str, help='folder of the datasets')
    parser.add_argument('dataset', choices=['train', 'test', 'review'],
                        help='name of the dataset to use')
    parser.add_argument('--output', '-o', type=str, default='output.txt',
                        help='filename of the result')
    parser.add_argument('--mode', '-m', choices=['train', 'infer'],
                        default='infer', help='mode of operation')
    parser.add_argument('--dry', '-d', action='store_true',
                        help='dry run only, the model is not saved')
    parser.add_argument('--reuse', '-r', action='store_true',
                        help='train upon existing model if exists')
    args = parser.parse_args()

    # fine tune the parameters
    model_name = 's2s'

    dataset = Video(args.folder, dtype=args.dataset)
    (n_features, n_words, n_timesteps) = dataset.shape

    with open(args.output, 'w') as fd:
        for vid in dataset._ids:
            fd.write('{},the\n'.format(vid))

    import sys
    sys.exit()

    if args.mode == 'train':
        if not args.reuse:
            archive(model_name)
        model = load(model_name)
        # build the model from scratch if nothing is loaded
        if not model:
            model = build(n_features=n_features, n_words=n_words, n_timesteps=n_timesteps, latent_dim=256)
        compile(model)
        train(model, dataset)
    elif args.mode == 'infer':
        model = load(model_name, strict=True)
        compile(model)

    evaluate(model, dataset)

    if not args.dry:
        save(model, model_name)
