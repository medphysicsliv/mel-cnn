from abc import ABC
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn import utils
from tensorflow import data
from hyperparameters import BATCH_SIZE_RANGE, HWC_RANGE

all_data = pd.read_csv('all_data.csv', index_col=0)
all_data.drop('dataset_id', axis=1, inplace=True)
all_data['image_type'].fillna('nan', inplace=True)
all_data['anatom_site_general'].fillna('nan', inplace=True)
all_data['sex'].fillna('nan', inplace=True)
all_data['age_approx'].fillna(1000, inplace=True)
all_data = utils.shuffle(all_data)  # Shuffle data

msk = np.random.rand(len(all_data)) < 0.8  # Split data to training and evaluation segments
training_data = all_data[msk][10000:11000]
eval_data = all_data[~msk][10000:11000]

anatom_site_dict = {'head neck': 0, 'torso': 1, 'lateral torso': 2, 'upper extremity': 3,
                    'lower extremity': 4, 'palms soles': 5, 'oral genital': 6, 'nan': 7}
image_type_dict = {'clinic': 0, 'derm': 1}
sex_dict = {'m': 0, 'f': 1, 'nan': 2}
classes_dict = {'NV': 0, "NNV": 1, "MEL": 2, "NMC": 3, "SUS": 4}


class MelData(tf.data.Dataset, ABC):

    @staticmethod
    def _data_gen(mode):  # cast to Tensors. image, image_type, sex, classes, anatom_site, age,
        mode = mode.decode("utf-8")
        data_dict = {'train': training_data,
                     'eval': eval_data}
        for mode_data in data_dict[mode].values:
            image = tf.convert_to_tensor(mode_data[0])
            image_type = tf.one_hot(image_type_dict[mode_data[1]], depth=len(image_type_dict), name='image_type')
            sex = tf.one_hot(sex_dict[mode_data[2]], depth=len(sex_dict), name='sex')
            anatom_site = tf.one_hot(anatom_site_dict[mode_data[4]], depth=len(anatom_site_dict), name='anatom_site')
            age = tf.expand_dims(tf.convert_to_tensor(mode_data[5], dtype=tf.float32, name='age'), axis=0)
            classes = tf.one_hot(classes_dict[mode_data[3]], depth=len(classes_dict), name='classes')
            yield image, image_type, sex, anatom_site, age, classes

    def __new__(cls, hparams, *args, **kwargs):
        train_eval_datasets = []
        for mode in ('train', 'eval'):
            dataset = data.Dataset.from_generator(cls._data_gen,
                                                  output_signature=(tf.TensorSpec(shape=[],
                                                                                  dtype=tf.string, name='image'),
                                                                    tf.TensorSpec(shape=len(image_type_dict),
                                                                                  dtype=tf.float32, name='image_type'),
                                                                    tf.TensorSpec(shape=len(sex_dict),
                                                                                  dtype=tf.float32, name='sex'),
                                                                    tf.TensorSpec(shape=len(anatom_site_dict),
                                                                                  dtype=tf.float32,
                                                                                  name=' anatom_site'),
                                                                    tf.TensorSpec(shape=[1],
                                                                                  dtype=tf.float32, name='age'),
                                                                    tf.TensorSpec(shape=len(classes_dict),
                                                                                  dtype=tf.float32, name='classes')),
                                                  args=[mode])
            dataset = dataset.prefetch(tf.data.AUTOTUNE)
            dataset = dataset.map(lambda image, image_type, sex, anatom_site, age, classes: (
                {'image': tf.image.resize_with_pad(tf.image.decode_image(tf.io.read_file(image)), hparams[HWC_RANGE], hparams[HWC_RANGE]),
                 'image_type': image_type, 'sex': sex, 'anatom_site': anatom_site, 'age': age},
                {'classes': classes}), num_parallel_calls=tf.data.AUTOTUNE)
            dataset = dataset.batch(hparams[BATCH_SIZE_RANGE]).cache()

            train_eval_datasets.append(dataset)
        return train_eval_datasets
